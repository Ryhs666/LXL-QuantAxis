"""
绩效指标计算

- 年化收益率
- 夏普比率
- 最大回撤
- 胜率
- 盈亏比
- 卡尔玛比率
"""

import math
from typing import List, Dict


def calc_all_metrics(daily_values: List[dict],
                     trade_log: List[dict],
                     initial_capital: float) -> dict:
    """
    计算全部绩效指标

    参数:
        daily_values: 每日净值记录 [{"date", "total_value", ...}, ...]
        trade_log: 交易记录 [{"action", "pnl", ...}, ...]
        initial_capital: 初始资金
    """
    if not daily_values:
        return {}

    total_values = [d["total_value"] for d in daily_values]
    final_value = total_values[-1]
    total_return = (final_value / initial_capital - 1) * 100

    # 年化收益率
    trading_days = len(daily_values)
    years = trading_days / 252
    annual_return = ((final_value / initial_capital) ** (1 / max(years, 0.01)) - 1) * 100

    # 计算日收益率序列
    daily_returns = []
    for i in range(1, len(total_values)):
        ret = (total_values[i] / total_values[i - 1] - 1)
        daily_returns.append(ret)

    # 最大回撤
    max_drawdown, max_dd_start, max_dd_end = _calc_max_drawdown(daily_values)

    # 夏普比率
    sharpe = _calc_sharpe(daily_returns, years)

    # 从交易记录计算胜率、盈亏比
    sells_with_pnl = [t for t in trade_log if t["action"] == "SELL" and "pnl" in t]
    wins = [t for t in sells_with_pnl if t["pnl"] > 0]
    losses = [t for t in sells_with_pnl if t["pnl"] <= 0]

    win_rate = len(wins) / len(sells_with_pnl) * 100 if sells_with_pnl else 0

    avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0
    profit_factor = (sum(t["pnl"] for t in wins) / abs(sum(t["pnl"] for t in losses))
                     if losses and sum(t["pnl"] for t in losses) != 0 else float("inf"))

    # 卡尔玛比率（年化收益 / 最大回撤）
    calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else float("inf")

    return {
        "初始资金": round(initial_capital, 2),
        "最终权益": round(final_value, 2),
        "总收益率": f"{total_return:+.2f}%",
        "年化收益率": f"{annual_return:+.2f}%",
        "夏普比率": round(sharpe, 2),
        "最大回撤": f"{max_drawdown:+.2f}%",
        "最大回撤区间": f"{max_dd_start} ~ {max_dd_end}",
        "卡尔玛比率": round(calmar, 2),
        "交易次数": len(trade_log),
        "卖出次数": len(sells_with_pnl),
        "盈利次数": len(wins),
        "亏损次数": len(losses),
        "胜率": f"{win_rate:.1f}%",
        "平均盈利": f"¥{avg_win:+,.2f}",
        "平均亏损": f"¥{avg_loss:+,.2f}",
        "盈亏比": f"{abs(avg_win / avg_loss):.2f}" if avg_loss != 0 else "∞",
        "盈利因子": f"{profit_factor:.2f}" if profit_factor != float("inf") else "∞",
    }


def _calc_max_drawdown(daily_values: List[dict]) -> tuple:
    """计算最大回撤及区间"""
    values = [d["total_value"] for d in daily_values]
    dates = [d["date"] for d in daily_values]

    peak = values[0]
    max_dd = 0
    dd_start = dates[0]
    dd_end = dates[0]
    temp_start = dates[0]

    for i, v in enumerate(values):
        if v > peak:
            peak = v
            temp_start = dates[i]

        dd = (peak - v) / peak * 100
        if dd > max_dd:
            max_dd = dd
            dd_start = temp_start
            dd_end = dates[i]

    return -max_dd, dd_start, dd_end


def _calc_sharpe(daily_returns: List[float], years: float) -> float:
    """计算夏普比率（假设无风险利率为 2%）"""
    if not daily_returns:
        return 0.0

    mean_ret = sum(daily_returns) / len(daily_returns)
    # 年化
    ann_mean = mean_ret * 252
    ann_std = _std(daily_returns) * math.sqrt(252)
    risk_free = 0.02

    if ann_std == 0:
        return 0.0
    return (ann_mean - risk_free) / ann_std


def _std(values: List[float]) -> float:
    """标准差"""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)
