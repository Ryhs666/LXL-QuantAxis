"""
AI 策略工厂 — 自我进化引擎

核心循环:
  1. 分析 → 扫描所有回测结果，发现盈利模式
  2. 生成 → AI 根据规律写新策略代码
  3. 进化 → 遗传算法: 杂交Top策略 + 随机突变
  4. 验证 → 自动回测新策略
  5. 保留 → 跑赢基准的进策略库
"""

import os, sys, json, time, re
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
import numpy as np

from src.config import config
from src.backtest.batch_runner import ResultDB
from src.backtest.data_feed import get_data
from src.backtest.engine import BacktestEngine
from src.models.strategy import StrategyConfig, Signal
from src.factors.definitions import FactorCalculator, FACTOR_REGISTRY
from src.factors.composer import SignalComposer
from src.ai.engine import LLMClient, QUANT_SYSTEM

BANK_DIR = os.path.join(config.data_dir, "strategy_bank")
os.makedirs(BANK_DIR, exist_ok=True)


# ============================================================
# 策略基因
# ============================================================

@dataclass
class StrategyGene:
    """一条策略基因 — 可被杂交和突变"""
    buy_factors: List[Dict] = field(default_factory=list)   # [{factor, op, threshold, weight}]
    sell_factors: List[Dict] = field(default_factory=list)
    buy_logic: str = "weighted"       # and / or / weighted
    buy_threshold: float = 2.0
    sell_logic: str = "or"
    sell_threshold: float = 0.5
    name: str = ""
    fitness: float = 0.0              # 夏普比率
    generation: int = 0
    parent: str = ""
    cross_symbol_performance: Dict[str, float] = field(default_factory=dict)  # {symbol: sharpe}
    is_validated: bool = False        # 已跨股票验证?
    regime_performance: Dict[int, float] = field(default_factory=dict)  # {regime_id: sharpe}

    def to_composer(self) -> SignalComposer:
        composer = SignalComposer(self.name or f"Gene_{id(self)}")
        for f in self.buy_factors:
            composer.add_condition(f["factor"], f.get("op", "lt"),
                                   f["threshold"], weight=f.get("weight", 1.0),
                                   action="BUY")
        composer.set_logic(self.buy_logic, self.buy_threshold, action="BUY")
        for f in self.sell_factors:
            composer.add_condition(f["factor"], f.get("op", "gt"),
                                   f["threshold"], weight=f.get("weight", 1.0),
                                   action="SELL")
        if self.sell_factors:
            composer.set_logic(self.sell_logic, self.sell_threshold, action="SELL")
        return composer

    def to_dict(self) -> dict:
        return {
            "name": self.name, "fitness": self.fitness,
            "generation": self.generation, "parent": self.parent,
            "buy_factors": self.buy_factors, "sell_factors": self.sell_factors,
            "buy_logic": self.buy_logic, "buy_threshold": self.buy_threshold,
            "sell_logic": self.sell_logic, "sell_threshold": self.sell_threshold,
            "cross_symbol_performance": self.cross_symbol_performance,
            "is_validated": self.is_validated,
            "regime_performance": self.regime_performance,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StrategyGene":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ============================================================
# 策略分析器
# ============================================================

class StrategyAnalyzer:
    """分析回测数据，提取盈利模式"""

    def __init__(self):
        self.db = ResultDB()

    def analyze(self) -> dict:
        """扫描所有回测结果，发现规律"""
        results = self.db.query(limit=500)
        if len(results) < 5:
            return {"status": "insufficient", "message": f"回测数据不足({len(results)}条)，至少需要5条"}

        df = pd.DataFrame(results)

        findings = {
            "总记录": len(results),
            "平均夏普": round(df["sharpe"].mean(), 2),
            "最佳夏普": round(df["sharpe"].max(), 2),
            "最佳收益": round(df["total_return"].max(), 1),
            "正收益占比": f"{len(df[df['total_return'] > 0]) / len(df) * 100:.0f}%",
        }

        # 按策略排名
        by_strat = df.groupby("strategy").agg(
            avg_sharpe=("sharpe", "mean"),
            avg_return=("total_return", "mean"),
            count=("sharpe", "count"),
        ).round(2).sort_values("avg_sharpe", ascending=False)

        findings["最佳策略"] = by_strat.index[0] if len(by_strat) > 0 else "N/A"
        findings["最佳策略夏普"] = round(by_strat.iloc[0]["avg_sharpe"], 2) if len(by_strat) > 0 else 0

        # 按标的排名
        by_sym = df.groupby("symbol").agg(
            avg_sharpe=("sharpe", "mean"),
            avg_return=("total_return", "mean"),
        ).round(2).sort_values("avg_sharpe", ascending=False)

        findings["最佳标的"] = by_sym.index[0] if len(by_sym) > 0 else "N/A"
        findings["最佳标的夏普"] = round(by_sym.iloc[0]["avg_sharpe"], 2) if len(by_sym) > 0 else 0

        # 模式发现
        patterns = []
        high_sharpe = df[df["sharpe"] > 0.3]
        if len(high_sharpe) > 0:
            # 哪种策略在标的上的高夏普最多
            pattern_counts = high_sharpe.groupby(["strategy", "symbol"]).size().sort_values(ascending=False)
            top_patterns = pattern_counts.head(5)
            for (strat, sym), cnt in top_patterns.items():
                avg_s = high_sharpe[(high_sharpe.strategy == strat) & (high_sharpe.symbol == sym)]["sharpe"].mean()
                patterns.append(f"{strat} @ {sym} (夏普{avg_s:.2f}, {cnt}次)")

        findings["盈利模式"] = patterns
        findings["策略排名"] = by_strat.to_dict()
        findings["标的排名"] = by_sym.to_dict()

        # 最佳策略的详细参数
        best = df.nlargest(3, "sharpe")
        findings["Top3"] = []
        for _, r in best.iterrows():
            findings["Top3"].append({
                "标的": r["symbol"], "策略": r["strategy"],
                "夏普": r["sharpe"], "收益": r["total_return"],
                "回撤": r["max_drawdown"], "胜率": r["win_rate"],
            })

        return findings

    def print_analysis(self):
        """打印分析报告"""
        a = self.analyze()
        print("\n" + "=" * 60)
        print("  AI 策略分析报告")
        print("=" * 60)
        print(f"  数据量: {a.get('总记录', 0)} 条回测记录")
        print(f"  最佳策略: {a.get('最佳策略', 'N/A')} (夏普 {a.get('最佳策略夏普', 0)})")
        print(f"  最佳标的: {a.get('最佳标的', 'N/A')} (夏普 {a.get('最佳标的夏普', 0)})")
        print(f"  正收益占比: {a.get('正收益占比', 'N/A')}")
        if a.get("盈利模式"):
            print(f"\n  发现的盈利模式:")
            for p in a["盈利模式"]:
                print(f"    - {p}")
        if a.get("Top3"):
            print(f"\n  TOP3 策略×标的组合:")
            for t in a["Top3"]:
                print(f"    {t['标的']} @ {t['策略']}: 夏普{t['夏普']:.2f} 收益{t['收益']:+.1f}%")


# ============================================================
# AI 策略生成器
# ============================================================

class StrategyGenerator:
    """用 AI 生成新策略"""

    def __init__(self):
        self.llm = LLMClient()
        self.analyzer = StrategyAnalyzer()
        self.generated = []

    def generate_from_analysis(self, n: int = 3) -> List[StrategyGene]:
        """基于回测分析，让 AI 创造新策略"""
        analysis = self.analyzer.analyze()

        if analysis.get("status") == "insufficient":
            print(f"  {analysis['message']}")
            return []

        # 列出可用因子
        factor_list = "\n".join([
            f"  - {name} [{f.category}]: {f.description}"
            for name, f in FACTOR_REGISTRY.items()
        ])

        prompt = f"""你是一个量化策略发明家。根据以下回测数据，创造{n}个新的交易策略。

## 回测分析结果
- 最佳策略: {analysis.get('最佳策略', 'N/A')} (夏普{analysis.get('最佳策略夏普', 0)})
- 最佳标的: {analysis.get('最佳标的', 'N/A')} (夏普{analysis.get('最佳标的夏普', 0)})
- 盈利模式: {analysis.get('盈利模式', [])}
- TOP3: {json.dumps(analysis.get('Top3', []), ensure_ascii=False)}

## 可用因子
{factor_list}

## 要求
创造{n}个新策略，每个策略必须:
1. 使用2-4个因子组合（买入条件）
2. 每个因子指定 operator(gt/lt)、threshold(0-1之间的数)、weight(1-5)
3. 指定逻辑: and/or/weighted + 触发阈值
4. 卖出条件也需1-2个因子
5. 给策略起一个中文名

返回纯JSON数组，格式:
[{{"name":"策略名","buy_factors":[{{"factor":"因子名","op":"lt","threshold":0.3,"weight":3}}],"buy_logic":"weighted","buy_threshold":3.0,"sell_factors":[{{"factor":"因子名","op":"gt","threshold":0.7,"weight":2}}],"sell_logic":"and"}}]

只返回JSON数组，不要其他文字。"""

        try:
            reply = self.llm.ask(prompt, system=QUANT_SYSTEM, temperature=0.8)
            # 提取 JSON
            json_match = re.search(r'\[[\s\S]*\]', reply)
            if json_match:
                genes_data = json.loads(json_match.group())
                genes = []
                for gd in genes_data:
                    gene = StrategyGene(
                        name=gd.get("name", "AI生成"),
                        buy_factors=gd.get("buy_factors", []),
                        sell_factors=gd.get("sell_factors", []),
                        buy_logic=gd.get("buy_logic", "weighted"),
                        buy_threshold=gd.get("buy_threshold", 3.0),
                        sell_logic=gd.get("sell_logic", "or"),
                        sell_threshold=gd.get("sell_threshold", 0.5),
                        generation=1,
                        parent="AI-Generator",
                    )
                    genes.append(gene)

                self.generated.extend(genes)
                return genes

        except Exception as e:
            print(f"  AI 生成失败: {e}")

        return []


# ============================================================
# 遗传进化器
# ============================================================

class GeneticEvolver:
    """遗传算法进化策略"""

    # 可用因子池
    FACTOR_POOL = list(FACTOR_REGISTRY.keys())
    OPS = ["gt", "lt"]

    def __init__(self, population_size: int = 20, elite_count: int = 4,
                 mutation_rate: float = 0.3, crossover_rate: float = 0.5):
        self.pop_size = population_size
        self.elite_count = elite_count
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.population: List[StrategyGene] = []
        self.generation = 0
        self.best_ever: Optional[StrategyGene] = None
        self.history: List[Dict] = []

    def initialize(self, seeds: List[StrategyGene] = None):
        """初始化种群"""
        self.population = []

        # 添加种子基因
        if seeds:
            for s in seeds[:self.elite_count]:
                s.generation = 0
                self.population.append(s)

        # 随机生成补足
        while len(self.population) < self.pop_size:
            gene = self._random_gene()
            gene.generation = 0
            self.population.append(gene)

    def _random_gene(self) -> StrategyGene:
        """随机生成一个策略基因"""
        n_buy = np.random.randint(2, 4)
        buy_factors = []
        for _ in range(n_buy):
            buy_factors.append({
                "factor": np.random.choice(self.FACTOR_POOL),
                "op": np.random.choice(self.OPS),
                "threshold": round(np.random.uniform(0.1, 0.9), 2),
                "weight": np.random.randint(1, 5),
            })

        n_sell = np.random.randint(1, 3)
        sell_factors = []
        for _ in range(n_sell):
            sell_factors.append({
                "factor": np.random.choice(self.FACTOR_POOL),
                "op": "gt",
                "threshold": round(np.random.uniform(0.5, 0.9), 2),
                "weight": np.random.randint(1, 3),
            })

        return StrategyGene(
            name=f"Evo_{np.random.randint(1000, 9999)}",
            buy_factors=buy_factors, sell_factors=sell_factors,
            buy_logic=np.random.choice(["weighted", "and", "or"]),
            buy_threshold=round(np.random.uniform(1.5, 5.0), 1),
            sell_logic=np.random.choice(["or", "and"]),
            sell_threshold=round(np.random.uniform(0.2, 1.5), 1),
        )

    def _crossover(self, a: StrategyGene, b: StrategyGene) -> StrategyGene:
        """杂交两个基因"""
        child = StrategyGene(
            name=f"X_{np.random.randint(1000, 9999)}",
            buy_factors=a.buy_factors[:len(a.buy_factors)//2] + b.buy_factors[len(b.buy_factors)//2:],
            sell_factors=a.sell_factors if np.random.random() > 0.5 else b.sell_factors,
            buy_logic=a.buy_logic if np.random.random() > 0.5 else b.buy_logic,
            buy_threshold=(a.buy_threshold + b.buy_threshold) / 2,
            sell_logic=a.sell_logic if np.random.random() > 0.5 else b.sell_logic,
            sell_threshold=(a.sell_threshold + b.sell_threshold) / 2,
            parent=f"{a.name}+{b.name}",
        )
        return child

    def _mutate(self, gene: StrategyGene) -> StrategyGene:
        """突变基因"""
        gene = StrategyGene(
            name=gene.name, buy_factors=list(gene.buy_factors),
            sell_factors=list(gene.sell_factors),
            buy_logic=gene.buy_logic, buy_threshold=gene.buy_threshold,
            sell_logic=gene.sell_logic, sell_threshold=gene.sell_threshold,
        )

        if np.random.random() < self.mutation_rate and gene.buy_factors:
            idx = np.random.randint(0, len(gene.buy_factors))
            gene.buy_factors[idx]["threshold"] = round(
                np.clip(gene.buy_factors[idx]["threshold"] + np.random.uniform(-0.2, 0.2), 0.05, 0.95), 2)

        if np.random.random() < self.mutation_rate:
            gene.buy_threshold = round(np.clip(gene.buy_threshold + np.random.uniform(-1, 1), 1.0, 8.0), 1)

        if np.random.random() < self.mutation_rate * 0.5:
            gene.buy_factors.append({
                "factor": np.random.choice(self.FACTOR_POOL),
                "op": np.random.choice(self.OPS),
                "threshold": round(np.random.uniform(0.1, 0.9), 2),
                "weight": np.random.randint(1, 4),
            })

        return gene

    def evolve_generation(self, symbol: str = "601398", start_date: str = "2024-01-01",
                          verbose: bool = True) -> List[StrategyGene]:
        """进化一代"""
        self.generation += 1
        if verbose:
            print(f"\n  === 第 {self.generation} 代进化 ===")

        # 1. 评估适应度
        data = get_data(symbol, "A股", start_date=start_date)
        for gene in self.population:
            try:
                composer = gene.to_composer()
                strategy = composer.to_strategy(StrategyConfig(name=symbol))
                engine = BacktestEngine()
                result = engine.run(strategy, data)
                sharpe = float(result["metrics"].get("夏普比率", -99))
                gene.fitness = sharpe if not np.isnan(sharpe) and not np.isinf(sharpe) else -99
            except Exception:
                gene.fitness = -99

        # 排序
        self.population.sort(key=lambda g: g.fitness, reverse=True)

        best = self.population[0]
        if self.best_ever is None or best.fitness > self.best_ever.fitness:
            self.best_ever = StrategyGene(
                name=best.name, buy_factors=list(best.buy_factors),
                sell_factors=list(best.sell_factors),
                buy_logic=best.buy_logic, buy_threshold=best.buy_threshold,
                sell_logic=best.sell_logic, sell_threshold=best.sell_threshold,
                fitness=best.fitness, generation=self.generation,
            )

        if verbose:
            print(f"  最佳: {best.name} 夏普={best.fitness:.2f}")
            print(f"  中位: {self.population[len(self.population)//2].fitness:.2f}")
            print(f"  史上最佳: {self.best_ever.name} 夏普={self.best_ever.fitness:.2f} (第{self.best_ever.generation}代)")

        # 2. 精英保留
        new_pop = []
        for i in range(min(self.elite_count, len(self.population))):
            elite = self.population[i]
            new_pop.append(StrategyGene(
                name=f"E{self.generation}_{elite.name}",
                buy_factors=list(elite.buy_factors), sell_factors=list(elite.sell_factors),
                buy_logic=elite.buy_logic, buy_threshold=elite.buy_threshold,
                sell_logic=elite.sell_logic, sell_threshold=elite.sell_threshold,
                generation=self.generation, parent=elite.name,
            ))

        # 3. 杂交+突变生成新一代
        while len(new_pop) < self.pop_size:
            if np.random.random() < self.crossover_rate and len(self.population) >= 2:
                parents = np.random.choice(self.population[:self.pop_size//2], 2, replace=False)
                child = self._crossover(parents[0], parents[1])
            else:
                child = self._random_gene()

            child = self._mutate(child)
            child.generation = self.generation
            new_pop.append(child)

        self.population = new_pop

        # 记录
        self.history.append({
            "generation": self.generation,
            "best_fitness": best.fitness,
            "median_fitness": self.population[len(self.population)//2].fitness,
            "best_gene": best.to_dict(),
        })

        return self.population

    def evolve(self, generations: int = 5, symbol: str = "601398",
               start_date: str = "2024-01-01", verbose: bool = True) -> dict:
        """多代进化"""
        if not self.population:
            self.initialize()

        if verbose:
            print(f"\n{'='*60}")
            print(f"  遗传算法进化 — {generations} 代 × {self.pop_size} 个体")
            print(f"  标的: {symbol} | 日期: {start_date}")
            print(f"{'='*60}")

        for _ in range(generations):
            self.evolve_generation(symbol, start_date, verbose)

        if verbose:
            print(f"\n  === 进化完成 ===")
            print(f"  史上最佳: {self.best_ever.name}")
            print(f"  夏普: {self.best_ever.fitness:.2f}")
            print(f"  买入因子: {self.best_ever.buy_factors}")
            print(f"  卖出因子: {self.best_ever.sell_factors}")

        return {
            "best": self.best_ever.to_dict() if self.best_ever else {},
            "history": self.history,
            "population_size": len(self.population),
            "generations": self.generation,
        }


# ============================================================
# 策略银行
# ============================================================

class StrategyBank:
    """存储和管理优秀策略"""

    def __init__(self):
        self.path = os.path.join(BANK_DIR, "bank.json")
        self.strategies: List[dict] = self._load()

    def _load(self) -> list:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.strategies, f, indent=2, ensure_ascii=False)

    def deposit(self, gene: StrategyGene, score: float, source: str = "unknown"):
        """存入策略"""
        entry = {
            "name": gene.name,
            "source": source,
            "fitness": gene.fitness,
            "score": score,
            "buy_factors": gene.buy_factors,
            "sell_factors": gene.sell_factors,
            "buy_logic": gene.buy_logic,
            "buy_threshold": gene.buy_threshold,
            "sell_logic": gene.sell_logic,
            "generation": gene.generation,
            "deposited_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        # 去重
        existing = [s for s in self.strategies if s["name"] == gene.name]
        for e in existing:
            self.strategies.remove(e)
        self.strategies.append(entry)
        # 排序
        self.strategies.sort(key=lambda s: s["fitness"], reverse=True)
        # 只保留前 50 个
        self.strategies = self.strategies[:50]
        self._save()

    def list_all(self) -> list:
        return self.strategies

    def get_best(self, n: int = 5) -> list:
        return self.strategies[:n]

    def find_by_factor(self, factor_name: str) -> list:
        result = []
        for s in self.strategies:
            factors = [f["factor"] for f in s.get("buy_factors", [])]
            if factor_name in factors:
                result.append(s)
        return result


# ============================================================
# 一键进化流程
# ============================================================

def auto_evolve(symbol: str = "601398", generations: int = 5,
                use_ai: bool = True, verbose: bool = True,
                revalidate: bool = True) -> dict:
    """
    一键自动进化

    流程:
      1. AI 分析回测数据
      2. AI 生成种子策略 (可选)
      3. 遗传算法进化
      4. 跨股票全市场复测 (新增)
      5. 最佳策略存入统一银行
    """
    from src.ai.bank_bridge import UnifiedStrategyBank
    bank = StrategyBank()
    unified = UnifiedStrategyBank()

    seeds = []
    if use_ai:
        if verbose:
            print("\n  [1/4] AI 分析回测数据 + 生成种子策略...")
        try:
            generator = StrategyGenerator()
            seeds = generator.generate_from_analysis(n=4)
            if verbose:
                print(f"    AI 生成了 {len(seeds)} 个种子策略")
            for s in seeds:
                print(f"    - {s.name}: {len(s.buy_factors)}买入因子 + {len(s.sell_factors)}卖出因子")
        except Exception as e:
            if verbose:
                print(f"    AI 生成失败: {e}，使用随机种子")

    # 遗传进化
    if verbose:
        print(f"\n  [2/4] 遗传算法进化 ({generations}代)...")

    evolver = GeneticEvolver(population_size=20)
    evolver.initialize(seeds)
    result = evolver.evolve(generations, symbol, verbose=verbose)

    best_gene_dict = result.get("best", {})
    best_gene = None
    if best_gene_dict:
        best_gene = StrategyGene.from_dict(best_gene_dict)

    # ── 第4步: 跨股票全市场复测 ──
    revalidate_results = None
    if revalidate and best_gene and best_gene.fitness > 0:
        if verbose:
            print(f"\n  [3/4] 跨股票全市场复测...")

        validation_symbols = ["601398", "000858", "600036", "600900", "000333",
                              "600519", "000001", "002415", "300750", "601318"]

        cross_results = {}
        composer = best_gene.to_composer()
        total_symbols = 0
        sharpe_sum = 0.0

        for vs in validation_symbols:
            if vs == symbol:
                continue  # 跳过进化用的标的
            try:
                from src.backtest.data_feed import get_data
                from src.backtest.engine import BacktestEngine
                data = get_data(vs, "A股", start_date="2024-01-01")
                if data is None or len(data) < 100:
                    continue
                r = BacktestEngine().run(composer.to_strategy(
                    __import__('src.models.strategy', fromlist=['StrategyConfig']).StrategyConfig(name=vs)
                ), data)
                m = r["metrics"]
                sh = float(str(m.get("夏普比率", -99)))
                cross_results[vs] = sh
                sharpe_sum += sh
                total_symbols += 1
                if verbose:
                    tag = "+" if sh > 0 else "-"
                    print(f"    {vs}: 夏普{sh:+.2f} {tag}")
            except Exception as e:
                if verbose:
                    print(f"    {vs}: 跳过 ({e})")
                cross_results[vs] = 0.0

        if total_symbols > 0:
            avg_sharpe = sharpe_sum / total_symbols
            best_gene.cross_symbol_performance = cross_results
            best_gene.is_validated = True
            best_gene.fitness = avg_sharpe  # 用跨股票平均替代单股票
            revalidate_results = {
                "symbols_tested": total_symbols,
                "cross_sharpe": round(avg_sharpe, 3),
                "best_symbol": max(cross_results, key=cross_results.get),
                "worst_symbol": min(cross_results, key=cross_results.get),
                "details": cross_results,
            }
            if verbose:
                print(f"    跨股票平均夏普: {avg_sharpe:+.3f} "
                      f"(最佳:{revalidate_results['best_symbol']}, "
                      f"最差:{revalidate_results['worst_symbol']})")

    # ── 第5步: 存入银行 ──
    if verbose:
        print(f"\n  [4/4] 存入策略银行...")

    if best_gene and (best_gene.is_validated or best_gene.fitness > 0):
        bank.deposit(best_gene, best_gene.fitness, source="evolution")
        # 也存入统一银行
        unified.deposit(best_gene.to_dict(), source="evolution")
        if verbose:
            validated_str = "(已跨市场验证)" if best_gene.is_validated else ""
            print(f"    OK 最佳策略 '{best_gene.name}' (夏普{best_gene.fitness:.2f}) 已入银行 {validated_str}")
            print(f"    银行共 {len(bank.list_all())} 个策略")
    else:
        if verbose:
            print("    WARN 没有生成有效策略")

    # 排名
    all_strategies = bank.list_all()
    if all_strategies and verbose:
        print(f"\n    策略银行 TOP 5:")
        for i, s in enumerate(all_strategies[:5], 1):
            print(f"    {i}. {s['name']} (夏普{s['fitness']:.2f}, 来源={s['source']})")

    return {
        "best": best_gene_dict,
        "evolution_history": evolver.history,
        "bank_size": len(bank.list_all()),
        "bank_top5": bank.get_best(5),
        "revalidate": revalidate_results,
    }


def show_bank():
    """展示策略银行"""
    bank = StrategyBank()
    strategies = bank.list_all()

    print("\n" + "=" * 60)
    print(f"  🏦 LXL 策略银行 (共 {len(strategies)} 个策略)")
    print("=" * 60)

    if not strategies:
        print("  📭 银行空。运行一次自动进化来存入策略。")
        return

    print(f"\n  {'排名':<4} {'名称':<25} {'夏普':<8} {'来源':<12} {'日期':<12}")
    print("  " + "-" * 61)
    for i, s in enumerate(strategies, 1):
        factors = ", ".join(f["factor"][:12] for f in s.get("buy_factors", [])[:3])
        print(f"  {i:<4} {s['name']:<25} {s['fitness']:>6.2f}  {s['source']:<12} {s.get('deposited_at','')[:10]:<12}")
        print(f"      买入: {factors}")
