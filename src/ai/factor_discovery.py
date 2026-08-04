# -*- coding: utf-8 -*-
"""
Genetic Factor Miner — 基于遗传编程的因子自动发现

自动演化出高 IC 的因子表达式。

集成方式:
    from src.ai.factor_discovery import GeneticFactorMiner, FactorValidator
    miner = GeneticFactorMiner(data, population_size=50, generations=20)
    result = miner.mine()
    print(result["best_factor"], result["best_ic"])
"""

import numpy as np
import pandas as pd
import random
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import warnings
import logging

warnings.filterwarnings("ignore")
logger = logging.getLogger("ai.factor_discovery")

try:
    from scipy.stats import spearmanr, pearsonr
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# ═══════════════════════════════════════════
# 表达式树
# ═══════════════════════════════════════════

class FactorNode:
    """因子表达式树节点"""
    pass


@dataclass
class OpNode(FactorNode):
    op: str
    left: FactorNode = None
    right: FactorNode = None

    def __repr__(self):
        return f"({self.left} {self.op} {self.right})"


@dataclass
class LeafNode(FactorNode):
    name: str
    params: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self):
        if self.params:
            items = ", ".join(f"{k}={v}" for k, v in self.params.items())
            return f"{self.name}({items})"
        return self.name


# ═══════════════════════════════════════════
# 因子评估器
# ═══════════════════════════════════════════

class FactorEvaluator:
    """将表达式树转为可执行函数, 计算因子值"""

    FEATURES = {
        "open": "开盘价", "high": "最高价", "low": "最低价",
        "close": "收盘价", "volume": "成交量",
    }

    INDICATORS = {
        "ma":     lambda d, p: d["close"].rolling(p).mean(),
        "ema":    lambda d, p: d["close"].ewm(span=p).mean(),
        "std":    lambda d, p: d["close"].rolling(p).std(),
        "max":    lambda d, p: d["close"].rolling(p).max(),
        "min":    lambda d, p: d["close"].rolling(p).min(),
        "pct":    lambda d, p: d["close"].pct_change(p),
        "roc":    lambda d, p: (d["close"] - d["close"].shift(p)) / d["close"].shift(p),
        "rank":   lambda d, p: d["close"].rolling(p).rank(pct=True),
    }

    def __init__(self, data: pd.DataFrame):
        self.data = data
        self._cache = {}

    def evaluate(self, node: FactorNode) -> pd.Series:
        if isinstance(node, LeafNode):
            return self._eval_leaf(node)
        elif isinstance(node, OpNode):
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)
            return self._apply_op(node.op, left, right)
        raise ValueError(f"未知节点: {type(node)}")

    def _eval_leaf(self, leaf: LeafNode) -> pd.Series:
        key = repr(leaf)
        if key in self._cache:
            return self._cache[key]
        name, params = leaf.name, leaf.params
        if name in self.FEATURES:
            result = self.data[name].copy().astype(float)
        elif name in self.INDICATORS:
            period = params.get("period", 20)
            result = self.INDICATORS[name](self.data, period)
        else:
            result = pd.Series(0.0, index=self.data.index)
        self._cache[key] = result
        return result

    @staticmethod
    def _apply_op(op: str, left: pd.Series, right: pd.Series) -> pd.Series:
        right = right.replace(0, np.nan) if op in ("/",) else right
        if op == "+": return left + right
        elif op == "-": return left - right
        elif op == "*": return left * right
        elif op == "/": return left / right
        raise ValueError(f"未知操作符: {op}")


# ═══════════════════════════════════════════
# 遗传编程因子挖掘器
# ═══════════════════════════════════════════

class GeneticFactorMiner:
    """基于遗传编程的因子自动发现"""

    def __init__(
        self,
        data: pd.DataFrame,
        feature_names: List[str] = None,
        population_size: int = 100,
        generations: int = 50,
        max_depth: int = 4,
        target_col: str = "close",
    ):
        self.data = data
        self.feature_names = feature_names or list(FactorEvaluator.FEATURES.keys())
        self.population_size = population_size
        self.generations = generations
        self.max_depth = max_depth

        # 目标: 未来1日收益
        self._future_returns = data[target_col].pct_change().shift(-1)

        self.best_tree = None
        self.best_fitness = -np.inf
        self.history = []

        logger.info(
            f"[Miner] 初始化: features={len(self.feature_names)}, "
            f"pop={population_size}, gens={generations}, max_depth={max_depth}"
        )

    def _random_tree(self, depth: int = 0) -> FactorNode:
        if depth >= self.max_depth:
            return self._random_leaf()
        if random.random() < 0.5:
            op = random.choice(["+", "-", "*", "/"])
            return OpNode(op, self._random_tree(depth + 1), self._random_tree(depth + 1))
        return self._random_leaf()

    def _random_leaf(self) -> LeafNode:
        name = random.choice(self.feature_names)
        if name in FactorEvaluator.INDICATORS:
            period = random.choice([5, 10, 20, 30, 60])
            return LeafNode(name, {"period": period})
        return LeafNode(name)

    def _fitness(self, tree: FactorNode) -> float:
        try:
            evaluator = FactorEvaluator(self.data)
            values = evaluator.evaluate(tree)
            mask = values.notna() & self._future_returns.notna()
            if mask.sum() < 10:
                return -1.0

            if HAS_SCIPY:
                ic, _ = spearmanr(values[mask], self._future_returns[mask])
                return ic if not np.isnan(ic) else -1.0

            # 无 scipy 回退: Pearson
            x, y = values[mask], self._future_returns[mask]
            corr = np.corrcoef(x, y)[0, 1]
            return corr if not np.isnan(corr) else -1.0
        except Exception:
            return -1.0

    def _collect_nodes(self, tree: FactorNode) -> list:
        nodes = [tree]
        if isinstance(tree, OpNode):
            nodes.extend(self._collect_nodes(tree.left))
            nodes.extend(self._collect_nodes(tree.right))
        return nodes

    def _tree_to_string(self, tree: FactorNode) -> str:
        if tree is None:
            return "None"
        if isinstance(tree, LeafNode):
            if tree.params:
                p = ", ".join(f"{k}={v}" for k, v in tree.params.items())
                return f"{tree.name}({p})"
            return tree.name
        elif isinstance(tree, OpNode):
            return f"({self._tree_to_string(tree.left)} {tree.op} {self._tree_to_string(tree.right)})"
        return ""

    def mine(self) -> Dict[str, Any]:
        """执行因子挖掘 (随机搜索)"""
        logger.info(f"[Miner] 开始挖掘 ({self.generations} 代)...")

        for gen in range(self.generations):
            gen_best_ic = -np.inf
            gen_best_tree = None

            for _ in range(max(5, self.population_size // 10)):
                tree = self._random_tree()
                ic = self._fitness(tree)

                if ic > gen_best_ic:
                    gen_best_ic = ic
                    gen_best_tree = tree
                if ic > self.best_fitness:
                    self.best_fitness = ic
                    self.best_tree = tree

            self.history.append(gen_best_ic)

        top = sorted([
            (self._tree_to_string(self.best_tree), self.best_fitness)
        ], key=lambda x: x[1], reverse=True)

        logger.info(f"[Miner] 完成: best_ic={self.best_fitness:.4f}, "
                     f"expr={self._tree_to_string(self.best_tree)}")
        return {
            "best_factor": self._tree_to_string(self.best_tree),
            "best_ic": round(self.best_fitness, 4),
            "history": [round(h, 4) for h in self.history],
            "top_factors": top,
        }


# ═══════════════════════════════════════════
# 因子验证器
# ═══════════════════════════════════════════

class FactorValidator:
    """因子有效性验证"""

    def __init__(self, data: pd.DataFrame):
        self.data = data
        self._future_returns = data["close"].pct_change().shift(-1)

    def validate(self, factor_values: pd.Series) -> Dict[str, Any]:
        mask = factor_values.notna() & self._future_returns.notna()
        if mask.sum() < 20:
            return {"error": "有效数据不足"}

        x, y = factor_values[mask], self._future_returns[mask]

        if HAS_SCIPY:
            ic, _ = spearmanr(x, y)
            pearson_ic, _ = pearsonr(x, y)
        else:
            ic = np.corrcoef(x.rank(), y.rank())[0, 1]
            pearson_ic = np.corrcoef(x, y)[0, 1]

        # 分层收益
        try:
            groups = pd.qcut(x, 5, labels=False, duplicates="drop")
            group_rets = [y[groups == g].mean() for g in range(5) if (groups == g).sum() > 0]
            long_short = group_rets[-1] - group_rets[0] if len(group_rets) >= 2 else 0
        except Exception:
            group_rets = []
            long_short = 0

        return {
            "ic": round(ic, 4) if not np.isnan(ic) else 0,
            "rank_ic": round(ic, 4),
            "pearson_ic": round(pearson_ic, 4),
            "long_short_spread": round(long_short, 6),
            "group_returns": [round(r, 6) for r in group_rets],
            "valid_obs": int(mask.sum()),
        }


# ═══════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════

def run_discover_cli(
    symbol: str = "600519",
    start_date: str = "2024-01-01",
    generations: int = 30,
    population: int = 80,
):
    """discover-factors CLI 入口"""
    from src.backtest.data_feed import get_data

    print(f"\n  [Miner] 加载数据: {symbol} ...")
    data = get_data(symbol, "A股", start_date=start_date)
    if data is None or len(data) < 200:
        print(f"  数据不足")
        return None

    miner = GeneticFactorMiner(
        data, population_size=population,
        generations=generations, max_depth=4,
    )
    result = miner.mine()

    print(f"\n  [Miner] 最佳因子: {result['best_factor']}")
    print(f"  [Miner] 最佳 IC: {result['best_ic']:.4f}")

    # 验证
    if result["best_factor"] != "None":
        evaluator = FactorEvaluator(data)
        tree = miner.best_tree
        if tree:
            values = evaluator.evaluate(tree)
            validator = FactorValidator(data)
            val = validator.validate(values)
            print(f"  [Validator] Rank IC: {val.get('rank_ic', 0):.4f}, "
                  f"Long/Short: {val.get('long_short_spread', 0):.6f}")

    return result
