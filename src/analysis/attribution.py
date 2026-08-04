# -*- coding: utf-8 -*-
"""
Brinson Attribution — 回测收益归因分析

将超额收益分解为:
  - 配置收益 (择时) — allocation effect
  - 选股收益          — selection effect
  - 交互收益 (残差)   — interaction effect

集成方式: BacktestEngine.run() 传入 benchmark_data 后自动调用。
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
import logging

logger = logging.getLogger("analysis.attribution")


class BrinsonAttribution:
    """Brinson 归因分析 (逐日多期)"""

    def __init__(self, benchmark_returns: pd.Series):
        """
        Args:
            benchmark_returns: 基准日收益率 (index=date)
        """
        self.benchmark = benchmark_returns

    def decompose(
        self,
        portfolio_returns: pd.Series,
        portfolio_weights: Optional[pd.DataFrame] = None,
        benchmark_weights: Optional[pd.DataFrame] = None,
        stock_returns: Optional[pd.DataFrame] = None,
    ) -> Dict[str, pd.Series]:
        """
        执行归因分解。

        简化模式 (无权重数据): 超额收益 = portfolio - benchmark (不分解)
        完整模式 (有权重数据): 分解为 allocation + selection + interaction
        """
        common = portfolio_returns.index.intersection(self.benchmark.index)
        if len(common) == 0:
            logger.warning("组合与基准日期无交集")
            return {}

        excess = pd.Series(np.nan, index=common, dtype=float)
        allocation = pd.Series(0.0, index=common, dtype=float)
        selection = pd.Series(0.0, index=common, dtype=float)
        interaction = pd.Series(0.0, index=common, dtype=float)

        has_weights = (
            portfolio_weights is not None
            and benchmark_weights is not None
            and stock_returns is not None
        )

        for dt in common:
            p_ret = portfolio_returns.loc[dt]
            b_ret = self.benchmark.loc[dt]
            excess.loc[dt] = p_ret - b_ret

            if not has_weights:
                continue

            # ── 完整 Brinson 分解 ──
            try:
                p_w = self._align_weights(portfolio_weights, dt, stock_returns)
                b_w = self._align_weights(benchmark_weights, dt, stock_returns)
                r_stocks = stock_returns.loc[dt].dropna()

                all_stocks = sorted(set(p_w.index) | set(b_w.index) | set(r_stocks.index))
                if not all_stocks:
                    continue

                p_w = p_w.reindex(all_stocks, fill_value=0.0)
                b_w = b_w.reindex(all_stocks, fill_value=0.0)
                r = r_stocks.reindex(all_stocks, fill_value=0.0)

                # Allocation = (Wp - Wb) * Rb
                allocation.loc[dt] = ((p_w - b_w) * b_ret).sum()
                # Selection   = Wb * (R - Rb)
                selection.loc[dt] = (b_w * (r - b_ret)).sum()
                # Interaction = (Wp - Wb) * (R - Rb)
                interaction.loc[dt] = ((p_w - b_w) * (r - b_ret)).sum()
            except Exception:
                pass

        return {
            "excess_return": excess.dropna(),
            "allocation": allocation,
            "selection": selection,
            "interaction": interaction,
        }

    @staticmethod
    def _align_weights(weights_df, date, stock_returns):
        """从权重 DataFrame 提取并对齐某日权重"""
        if date in weights_df.index:
            w = weights_df.loc[date]
        else:
            # 用最近的非空日期
            prev = weights_df.loc[:date]
            if prev.empty:
                return pd.Series(dtype=float)
            w = prev.iloc[-1]
        if isinstance(w, pd.DataFrame):
            w = w.iloc[0]
        return w.dropna() if hasattr(w, 'dropna') else pd.Series(w).dropna()

    def summary(self, decomposition: Dict[str, pd.Series]) -> Dict[str, float]:
        """归因摘要"""
        excess = decomposition.get("excess_return", pd.Series())
        alloc = decomposition.get("allocation", pd.Series())
        sel = decomposition.get("selection", pd.Series())
        inter = decomposition.get("interaction", pd.Series())

        total_excess = excess.sum()
        total_alloc = alloc.sum()
        total_sel = sel.sum()
        total_inter = inter.sum()

        if abs(total_excess) > 1e-8:
            return {
                "total_excess_pct": round(total_excess * 100, 4),
                "allocation_contribution_pct": round(total_alloc * 100, 4),
                "selection_contribution_pct": round(total_sel * 100, 4),
                "interaction_contribution_pct": round(total_inter * 100, 4),
                "allocation_share_pct": round(total_alloc / total_excess * 100, 1),
                "selection_share_pct": round(total_sel / total_excess * 100, 1),
                "interaction_share_pct": round(total_inter / total_excess * 100, 1),
                "dominant_effect": (
                    "选股" if abs(total_sel) >= abs(total_alloc) else "择时"
                ),
            }
        return {
            "total_excess_pct": 0.0,
            "dominant_effect": "无显著超额",
        }


# ═══════════════════════════════════════════
# 引擎集成入口
# ═══════════════════════════════════════════

def compute_attribution_from_engine(
    portfolio_daily_values: List[dict],
    benchmark_values: List[dict],
    returns_df: Optional[pd.DataFrame] = None,
) -> Optional[Dict]:
    """
    从引擎产出的 daily_values 和 benchmark_values 计算归因。

    Args:
        portfolio_daily_values: BacktestEngine 产出的 portfolio.daily_values
        benchmark_values:       基准净值序列 [{date, total_value}, ...]
        returns_df:             个股收益率 (可选, 用于完整分解)

    Returns:
        归因摘要 dict, 或 None
    """
    if not portfolio_daily_values or not benchmark_values:
        return None

    try:
        # 构建组合收益率序列
        port_vals = [d["total_value"] for d in portfolio_daily_values]
        port_ret = pd.Series(
            [port_vals[i] / port_vals[i-1] - 1 for i in range(1, len(port_vals))],
            index=[d["date"] for d in portfolio_daily_values[1:]],
        )

        # 构建基准收益率序列
        bench_vals = [d["total_value"] for d in benchmark_values]
        bench_ret = pd.Series(
            [bench_vals[i] / bench_vals[i-1] - 1 for i in range(1, len(bench_vals))],
            index=[d["date"] for d in benchmark_values[1:]],
        )

        attr = BrinsonAttribution(bench_ret)
        decomp = attr.decompose(port_ret)
        if decomp:
            return attr.summary(decomp)
    except Exception as e:
        logger.warning(f"归因计算异常: {e}")

    return None
