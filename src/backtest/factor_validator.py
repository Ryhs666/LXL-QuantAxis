"""
FactorValidator — 因子有效性验证 (v5.6)

1. IC 分析: 因子值与未来N日收益的 Spearman 相关系数
2. 分层回测: 按因子分5组, 绘制累计收益曲线
3. 报表输出: IC均值/标准差/IC_IR/胜率
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict
import warnings
warnings.filterwarnings('ignore')


def _spearmanr(x, y):
    """纯 numpy Spearman 相关系数 (不依赖 scipy)"""
    if len(x) < 3:
        return np.nan, np.nan
    # Rank
    x_rank = np.argsort(np.argsort(x)).astype(float) + 1
    y_rank = np.argsort(np.argsort(y)).astype(float) + 1
    # Pearson on ranks
    n = len(x_rank)
    mx = x_rank.mean(); my = y_rank.mean()
    num = ((x_rank - mx) * (y_rank - my)).sum()
    den = np.sqrt(((x_rank - mx)**2).sum() * ((y_rank - my)**2).sum())
    if den == 0:
        return np.nan, np.nan
    r = num / den
    return r, 1.0


class FactorValidator:
    """因子有效性验证器"""

    def __init__(self, factor_data: pd.DataFrame, price_data: pd.DataFrame,
                 min_stocks: int = 5):
        """
        factor_data: DataFrame, index=date, columns=symbol, values=因子值
        price_data:  DataFrame, index=date, columns=symbol, values=收盘价
        min_stocks:  最少需要多少只股票才计算IC (默认5)
        """
        self.factor = factor_data.copy()
        self.price = price_data.copy()
        self.min_stocks = min_stocks
        # 对齐日期
        common_dates = self.factor.index.intersection(self.price.index)
        self.factor = self.factor.loc[common_dates]
        self.price = self.price.loc[common_dates]

    # ═══════════════════════════════════════════
    # 1. IC 分析
    # ═══════════════════════════════════════════

    def compute_ic(self, forward_days: int = 5) -> pd.Series:
        """
        计算每日 IC (Spearman Rank Correlation)
        IC_t = corr(factor_t, return_{t+1 to t+N})
        """
        # 计算未来收益率
        future_ret = self.price.pct_change(forward_days).shift(-forward_days)
        # 对齐
        common_dates = self.factor.index.intersection(future_ret.dropna(how='all').index)

        ic_series = pd.Series(index=common_dates, dtype=float)

        for date in common_dates:
            fv = self.factor.loc[date]
            rv = future_ret.loc[date]
            valid = fv.notna() & rv.notna()
            if valid.sum() < self.min_stocks:
                ic_series[date] = np.nan
                continue
            try:
                ic, _ = _spearmanr(fv[valid].values, rv[valid].values)
                ic_series[date] = ic if not np.isnan(ic) else np.nan
            except Exception:
                ic_series[date] = np.nan

        return ic_series.dropna()

    def ic_summary(self, periods: List[int] = [1, 5, 20]) -> pd.DataFrame:
        """
        多周期 IC 汇总表
        返回: DataFrame (period x [IC_mean, IC_std, IC_IR, win_rate])
        """
        rows = []
        for p in periods:
            ic = self.compute_ic(forward_days=p)
            if len(ic) == 0:
                rows.append({"周期": f"{p}日", "IC均值": np.nan, "IC标准差": np.nan,
                             "IC_IR": np.nan, "胜率(%)": np.nan, "样本数": 0})
                continue
            ic_mean = ic.mean()
            ic_std = ic.std()
            ic_ir = ic_mean / ic_std if ic_std > 0 else 0
            win_rate = (ic > 0).sum() / len(ic) * 100
            rows.append({
                "周期": f"{p}日",
                "IC均值": round(ic_mean, 4),
                "IC标准差": round(ic_std, 4),
                "IC_IR": round(ic_ir, 2),
                "胜率(%)": round(win_rate, 1),
                "样本数": len(ic),
            })

        return pd.DataFrame(rows)

    def print_ic_report(self, periods: List[int] = [1, 5, 20]) -> pd.DataFrame:
        """打印 IC 分析报告"""
        df = self.ic_summary(periods)
        print("\n" + "=" * 65)
        print("  Factor IC Analysis Report")
        print("=" * 65)
        print(df.to_string(index=False))
        print("-" * 65)
        # 判断有效性
        best = df[df["IC均值"].notna()]
        if len(best) > 0:
            max_ir = best["IC_IR"].max()
            if max_ir > 0.5:
                print(f"  Conclusion: Strong Factor (IC_IR={max_ir:.2f} > 0.5)")
            elif max_ir > 0.3:
                print(f"  Conclusion: Moderate Factor (IC_IR={max_ir:.2f})")
            elif max_ir > 0.1:
                print(f"  Conclusion: Weak Factor (IC_IR={max_ir:.2f})")
            else:
                print(f"  Conclusion: Ineffective Factor (IC_IR={max_ir:.2f})")
        print("=" * 65)
        return df

    # ═══════════════════════════════════════════
    # 2. 分层回测
    # ═══════════════════════════════════════════

    def stratified_backtest(self, n_groups: int = 5,
                            forward_days: int = 5) -> Dict[str, pd.Series]:
        """
        按因子值分层回测
        每期将股票按因子值分为 N 组, 持有 forward_days 天
        返回: {group_name: cumulative_return_series}
        """
        future_ret = self.price.pct_change(forward_days).shift(-forward_days)
        common_dates = self.factor.index.intersection(future_ret.dropna(how='all').index)

        # 初始化各组累计收益
        group_returns = {f"Q{i+1}": pd.Series(0.0, index=common_dates) for i in range(n_groups)}
        group_returns["Q1-Q5"] = pd.Series(0.0, index=common_dates)  # 多空

        for date in common_dates:
            fv = self.factor.loc[date]
            rv = future_ret.loc[date]
            valid = fv.notna() & rv.notna()
            if valid.sum() < self.min_stocks:
                continue

            # 分组
            valid_fv = fv[valid]
            labels = pd.qcut(valid_fv, n_groups, labels=[f"Q{i+1}" for i in range(n_groups)])

            for q in range(1, n_groups + 1):
                q_stocks = labels[labels == f"Q{q}"].index
                if len(q_stocks) > 0:
                    group_returns[f"Q{q}"][date] = rv[q_stocks].mean()

            # 多空: Q1(最高因子) - Q5(最低因子)
            q1_stocks = labels[labels == f"Q{n_groups}"].index
            q5_stocks = labels[labels == "Q1"].index
            if len(q1_stocks) > 0 and len(q5_stocks) > 0:
                group_returns["Q1-Q5"][date] = rv[q1_stocks].mean() - rv[q5_stocks].mean()

        # 转为累计收益
        result = {}
        for name, ret_series in group_returns.items():
            cumulative = (1 + ret_series.fillna(0)).cumprod()
            result[name] = cumulative

        return result

    def plot_stratified(self, n_groups: int = 5, forward_days: int = 5,
                        save_path: str = None, title: str = "Factor Stratified Backtest"):
        """
        绘制分层回测累计收益曲线
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')
        except ImportError:
            print("matplotlib not installed")
            return

        results = self.stratified_backtest(n_groups, forward_days)

        fig, ax = plt.subplots(figsize=(14, 7))

        colors = ['#ef4444', '#f59e0b', '#94a3b8', '#3b82f6', '#10b981']
        for i in range(1, n_groups + 1):
            name = f"Q{i}"
            if name in results:
                ax.plot(results[name].index, results[name].values,
                        label=name, color=colors[i-1], linewidth=1.5)

        # 多空
        if "Q1-Q5" in results:
            ax2 = ax.twinx()
            ax2.plot(results["Q1-Q5"].index, results["Q1-Q5"].values,
                     label='Long-Short (Q5-Q1)', color='#8b5cf6', linewidth=2, linestyle='--')
            ax2.set_ylabel('Long-Short Cumulative', color='#8b5cf6')
            ax2.legend(loc='upper right')

        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Cumulative Return')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.axhline(y=1.0, color='gray', linestyle=':', alpha=0.5)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        return fig

    # ═══════════════════════════════════════════
    # 3. 综合报告
    # ═══════════════════════════════════════════

    def full_report(self, forward_days: int = 5, n_groups: int = 5,
                    save_chart: str = None) -> dict:
        """
        生成完整验证报告
        """
        # IC 分析
        ic = self.compute_ic(forward_days)
        ic_mean = ic.mean()
        ic_std = ic.std()
        ic_ir = ic_mean / ic_std if ic_std > 0 else 0
        win_rate = (ic > 0).sum() / len(ic) * 100 if len(ic) > 0 else 0

        # 分层回测
        stratified = self.stratified_backtest(n_groups, forward_days)

        # 最近 IC
        recent_ic = ic.tail(20).mean() if len(ic) >= 20 else ic_mean

        report = {
            "IC均值": round(ic_mean, 4),
            "IC标准差": round(ic_std, 4),
            "IC_IR": round(ic_ir, 2),
            "IC胜率(%)": round(win_rate, 1),
            "IC样本数": len(ic),
            "最近20日IC均值": round(recent_ic, 4),
            "有效性": "强" if ic_ir > 0.5 else ("中" if ic_ir > 0.3 else ("弱" if ic_ir > 0.1 else "无效")),
        }

        # 分层收益
        if stratified:
            report["Q5(最高因子)终值"] = round(stratified.get("Q5", pd.Series([1])).iloc[-1], 3)
            report["Q1(最低因子)终值"] = round(stratified.get("Q1", pd.Series([1])).iloc[-1], 3)
            report["多空收益(Q5-Q1)"] = round(
                stratified.get("Q1-Q5", pd.Series([0])).iloc[-1] - 1, 4)

        # 打印
        print("\n" + "=" * 50)
        print("  Factor Validation Report")
        print("=" * 50)
        for k, v in report.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.4f}" if abs(v) < 10 else f"  {k}: {v:.2f}")
            else:
                print(f"  {k}: {v}")
        print("=" * 50)

        # 绘图
        if save_chart:
            self.plot_stratified(n_groups, forward_days, save_chart)

        return report
