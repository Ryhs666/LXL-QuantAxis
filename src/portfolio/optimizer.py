# -*- coding: utf-8 -*-
"""
Portfolio Optimizer — 策略组合与资金分配优化器

支持: 等权 / 风险平价 / 均值-方差 / 分层风险平价 (HRP)
对接 src/strategies/ 中的具体策略类。

集成方式:
    python main.py --allocate  # 显示策略权重分配结果
    python main.py --allocate --method hrp  # 指定方法
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger("portfolio.optimizer")


@dataclass
class StrategyPerformance:
    name: str
    returns: pd.Series = None
    weight: float = 0.0
    sharpe: float = 0.0


class PortfolioOptimizer:
    """组合优化器 — 风险平价/均值-方差/HRP"""

    def __init__(self, strategies: Dict[str, pd.Series], risk_free_rate: float = 0.03):
        self.strategy_returns = strategies
        self.names = list(strategies.keys())
        self.returns_df = pd.DataFrame(strategies).dropna()
        self.cov_matrix = self.returns_df.cov() * 252
        self.mean_returns = self.returns_df.mean() * 252
        self.risk_free = risk_free_rate
        logger.info(f"Optimizer: {len(self.names)} strategies, {len(self.returns_df)} obs")

    def equal_weight(self) -> Dict[str, float]:
        n = len(self.names)
        return {name: 1.0 / n for name in self.names}

    def risk_parity(self) -> Dict[str, float]:
        n = len(self.names)
        if n == 1:
            return {self.names[0]: 1.0}

        try:
            from scipy.optimize import minimize
            def objective(w):
                w = np.array(w)
                pvar = w @ self.cov_matrix @ w.T
                mrc = self.cov_matrix @ w.T
                rc = w * mrc
                target = pvar / n
                return np.sum((rc - target) ** 2)

            result = minimize(
                objective, np.ones(n) / n,
                method='SLSQP',
                bounds=[(0, 1)] * n,
                constraints=[{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}],
            )
            weights = result.x if result.success else np.ones(n) / n
        except ImportError:
            # 无 scipy: 反波动率加权
            vols = np.sqrt(np.diag(self.cov_matrix))
            inv_vols = 1.0 / np.maximum(vols, 1e-8)
            weights = inv_vols / inv_vols.sum()

        return {name: float(weights[i]) for i, name in enumerate(self.names)}

    def mean_variance(self, target_return: float = None) -> Dict[str, float]:
        n = len(self.names)
        if n == 1:
            return {self.names[0]: 1.0}

        try:
            from scipy.optimize import minimize
            def neg_sharpe(w):
                w = np.array(w)
                pr = np.sum(w * self.mean_returns)
                pv = np.sqrt(w @ self.cov_matrix @ w.T)
                return -(pr - self.risk_free) / max(pv, 1e-8)

            result = minimize(
                neg_sharpe, np.ones(n) / n,
                method='SLSQP',
                bounds=[(0, 1)] * n,
                constraints=[{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}],
            )
            weights = result.x if result.success else np.ones(n) / n
        except ImportError:
            weights = np.ones(n) / n

        return {name: float(weights[i]) for i, name in enumerate(self.names)}

    def hierarchical_risk_parity(self) -> Dict[str, float]:
        try:
            from scipy.cluster.hierarchy import linkage, fcluster
            from scipy.spatial.distance import squareform
        except ImportError:
            return self.risk_parity()

        corr = self.returns_df.corr().fillna(0)
        dist = np.sqrt(0.5 * (1 - corr))
        dist_cond = squareform(dist.values, checks=False)
        linkage_m = linkage(dist_cond, method='single')
        clusters = fcluster(linkage_m, t=0.5, criterion='distance')

        weights = {}
        unique_c = np.unique(clusters)
        for cl in unique_c:
            members = [self.names[i] for i in np.where(clusters == cl)[0]]
            cl_w = 1.0 / len(unique_c)
            if len(members) == 1:
                weights[members[0]] = cl_w
            else:
                sub_returns = {m: self.strategy_returns[m] for m in members}
                sub = PortfolioOptimizer(sub_returns)
                sub_w = sub.risk_parity()
                for m, w in sub_w.items():
                    weights[m] = w * cl_w

        total = sum(weights.values())
        return {k: v / total for k, v in weights.items()} if total > 0 else self.equal_weight()

    def allocate(self, method: str = "risk_parity") -> Dict[str, float]:
        methods = {
            "equal": self.equal_weight,
            "risk_parity": self.risk_parity,
            "mean_variance": self.mean_variance,
            "hrp": self.hierarchical_risk_parity,
        }
        fn = methods.get(method, self.risk_parity)
        return fn()


# ═══════════════════════════════════════════
# 策略组合执行器 — 对接 src/strategies/
# ═══════════════════════════════════════════

class StrategyEnsemble:
    """策略组合 — 加权合并多个策略信号"""

    def __init__(self, strategy_instances: Dict[str, Any],
                 optimizer: PortfolioOptimizer = None,
                 weights: Dict[str, float] = None,
                 method: str = "risk_parity"):
        self.strategies = strategy_instances
        self.optimizer = optimizer
        self.method = method
        self.weights = weights or (
            optimizer.allocate(method) if optimizer else
            {n: 1.0 / len(strategy_instances) for n in strategy_instances}
        )

    def generate_combined_signal(self, data: pd.DataFrame, portfolio=None) -> dict:
        """
        综合各策略信号, 按权重合并。
        每个策略应有 on_bar(i, data, portfolio) 方法返回 Signal 或 None。
        """
        from src.models.strategy import Signal
        signals = []
        for name, strategy in self.strategies.items():
            w = self.weights.get(name, 0)
            if w <= 0:
                continue
            try:
                sig = strategy.on_bar(len(data) - 1, data, portfolio)
                if sig and isinstance(sig, Signal):
                    signals.append((sig, w))
            except Exception as e:
                logger.warning(f"策略 {name} 评估异常: {e}")

        if not signals:
            return None

        # 加权投票: BUY vs SELL 累计权重
        buy_weight = sum(w for s, w in signals if s.action == "BUY")
        sell_weight = sum(w for s, w in signals if s.action == "SELL")

        if buy_weight > sell_weight and buy_weight > 0.3:
            return {"action": "BUY", "confidence": buy_weight, "components": len(signals)}
        elif sell_weight > buy_weight and sell_weight > 0.3:
            return {"action": "SELL", "confidence": sell_weight, "components": len(signals)}
        return {"action": "HOLD", "confidence": max(buy_weight, sell_weight), "components": len(signals)}

    def rebalance_weights(self, returns_dict: Dict[str, pd.Series]):
        """用新收益率数据重新计算权重"""
        self.optimizer = PortfolioOptimizer(returns_dict)
        self.weights = self.optimizer.allocate(self.method)


# ═══════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════

def build_optimizer_from_backtest_db() -> Optional[PortfolioOptimizer]:
    """从回测数据库构建优化器 (对接 src/strategies/ 中实际策略)"""
    try:
        from src.backtest.batch_runner import ResultDB
        db = ResultDB()
        results = db.query(limit=200)
        if len(results) < 3:
            return None

        # 按策略分组, 用各结果的总收益率作为回报序列
        by_strategy: Dict[str, list] = {}
        for r in results:
            sname = r.get("strategy", "unknown")
            ret_str = str(r.get("total_return", "0%")).replace("%", "").replace("+", "")
            try:
                ret = float(ret_str) / 100
            except ValueError:
                ret = 0.0
            by_strategy.setdefault(sname, []).append(ret)

        # 构建收益率序列
        strategy_returns = {}
        for name, rets in by_strategy.items():
            if len(rets) >= 2:
                strategy_returns[name] = pd.Series(rets)

        if len(strategy_returns) < 2:
            return None

        return PortfolioOptimizer(strategy_returns)
    except Exception as e:
        logger.warning(f"无法从回测DB构建优化器: {e}")
        return None


def run_allocate_cli(method: str = "risk_parity"):
    """--allocate CLI 入口"""
    opt = build_optimizer_from_backtest_db()
    if opt is None:
        print("  回测数据不足, 无法计算最优权重")
        return

    weights = opt.allocate(method)
    print(f"\n═══ 策略权重分配 ({method}) ═══")
    total = sum(weights.values())
    for name, w in sorted(weights.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * max(1, int(w * 50))
        print(f"  {name:<20} {w:>6.1%}  {bar}")

    # 同时显示其他方法对比
    print(f"\n── 方法对比 ──")
    print(f"  {'策略':<20} {'等权':>6} {'风险平价':>8} {'均值方差':>8} {'HRP':>8}")
    eq = opt.equal_weight()
    rp = opt.risk_parity()
    mv = opt.mean_variance()
    hrp = opt.hierarchical_risk_parity()
    for name in weights:
        print(f"  {name:<20} {eq.get(name,0):>6.1%} {rp.get(name,0):>8.1%} "
              f"{mv.get(name,0):>8.1%} {hrp.get(name,0):>8.1%}")
