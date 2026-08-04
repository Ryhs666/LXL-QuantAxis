"""
绩效指标计算

绝对指标:
- 年化收益率 (CAGR)
- 夏普比率 (Sharpe Ratio) — 无风险利率可配置
- 索提诺比率 (Sortino Ratio)
- 最大回撤 (Max Drawdown)
- 卡尔玛比率 (Calmar Ratio)
- 胜率 / 盈亏比 / 盈利因子

基准相对指标 (需传入 benchmark_values):
- Alpha — 超额收益 (CAPM)
- Beta — 市场敏感度
- Tracking Error — 跟踪误差
- Information Ratio — 信息比率
- 基准收益率
- 超额年化收益率
"""

import math
from typing import List, Dict, Optional


def calc_all_metrics(daily_values: List[dict],
                     trade_log: List[dict],
                     initial_capital: float,
                     risk_free_rate: float = 0.02,
                     benchmark_values: Optional[List[dict]] = None) -> dict:
    """
    计算全部绩效指标

    参数:
        daily_values:     每日净值记录 [{"date", "total_value", ...}, ...]
        trade_log:        交易记录 [{"action", "pnl", ...}, ...]
        initial_capital:  初始资金
        risk_free_rate:   年化无风险利率 (默认2%, 可用国债收益率替代)
        benchmark_values: 基准每日净值 (同 daily_values 格式, 可选)
                          传入后计算 Alpha/Beta/IR/Tracking Error
    """
    if not daily_values:
        return {}

    total_values = [d["total_value"] for d in daily_values]
    final_value = total_values[-1]
    total_return = (final_value / initial_capital - 1) * 100

    # 年化收益率 (CAGR)
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

    # 夏普比率 & 索提诺比率 (使用可配置的无风险利率)
    sharpe, sortino = _calc_sharpe_and_sortino(daily_returns, years, risk_free_rate)

    # 从交易记录计算胜率、盈亏比
    sells_with_pnl = [t for t in trade_log if t["action"] == "SELL" and "pnl" in t]
    wins = [t for t in sells_with_pnl if t["pnl"] > 0]
    losses = [t for t in sells_with_pnl if t["pnl"] <= 0]

    win_rate = len(wins) / len(sells_with_pnl) * 100 if sells_with_pnl else 0

    avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0
    profit_factor = (sum(t["pnl"] for t in wins) / abs(sum(t["pnl"] for t in losses))
                     if losses and sum(t["pnl"] for t in losses) != 0 else float("inf"))

    # 卡尔玛比率
    calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 and annual_return != 0 else 0.0
    if calmar == float("inf") or calmar == float("-inf"):
        calmar = 0.0

    # 最大连续亏损次数
    max_consecutive_losses = 0
    current_streak = 0
    for t in trade_log:
        if t.get("action") == "SELL" and "pnl" in t:
            if t["pnl"] <= 0:
                current_streak += 1
                max_consecutive_losses = max(max_consecutive_losses, current_streak)
            else:
                current_streak = 0

    result = {
        "初始资金": round(initial_capital, 2),
        "最终权益": round(final_value, 2),
        "总收益率": f"{total_return:+.2f}%",
        "年化收益率": f"{annual_return:+.2f}%",
        "夏普比率": round(sharpe, 2),
        "索提诺比率": round(sortino, 2),
        "最大回撤": f"{max_drawdown:+.2f}%",
        "最大回撤区间": f"{max_dd_start} ~ {max_dd_end}",
        "卡尔玛比率": round(calmar, 2),
        "交易次数": len(trade_log),
        "卖出次数": len(sells_with_pnl),
        "盈利次数": len(wins),
        "亏损次数": len(losses),
        "最大连续亏损": max_consecutive_losses,
        "胜率": f"{win_rate:.1f}%",
        "平均盈利": f"¥{avg_win:+,.2f}",
        "平均亏损": f"¥{avg_loss:+,.2f}",
        "盈亏比": f"{abs(avg_win / avg_loss):.2f}" if avg_loss != 0 else "∞",
        "盈利因子": f"{profit_factor:.2f}" if profit_factor != float("inf") else "∞",
        "无风险利率": f"{risk_free_rate*100:.1f}%",
    }

    # ═══════════════════════════════════════════════
    # 基准相对指标 (Alpha / Beta / IR / Tracking Error)
    # ═══════════════════════════════════════════════
    if benchmark_values and len(benchmark_values) >= 2:
        bench_metrics = _calc_benchmark_metrics(
            daily_returns, benchmark_values, risk_free_rate, years)
        result.update(bench_metrics)

    return result


def _calc_benchmark_metrics(portfolio_returns: List[float],
                             benchmark_values: List[dict],
                             risk_free_rate: float,
                             years: float) -> dict:
    """
    计算基准相对指标

    Alpha = Rp - [Rf + Beta * (Rb - Rf)]  (年化)
    Beta  = Cov(Rp, Rb) / Var(Rb)
    TE    = std(Rp - Rb) * sqrt(252)      (年化跟踪误差)
    IR    = (Rp - Rb) / TE               (年化信息比率)
    """
    bench_values = [d["total_value"] for d in benchmark_values]
    bench_returns = []
    for i in range(1, len(bench_values)):
        ret = (bench_values[i] / bench_values[i - 1] - 1)
        bench_returns.append(ret)

    # 对齐长度 (取较短的那个)
    n = min(len(portfolio_returns), len(bench_returns))
    if n < 2:
        return {}
    rp = portfolio_returns[-n:]
    rb = bench_returns[-n:]

    # 日均收益
    mean_rp = sum(rp) / n
    mean_rb = sum(rb) / n

    # 年化收益
    ann_rp = mean_rp * 252
    ann_rb = mean_rb * 252

    # Beta = Cov(Rp, Rb) / Var(Rb)
    cov = _covariance(rp, rb)
    var_rb = _variance(rb)
    beta = cov / var_rb if var_rb > 0 else 0.0

    # Alpha (年化, CAPM)
    # Alpha = Rp - [Rf + Beta * (Rb - Rf)]
    alpha = (ann_rp - risk_free_rate - beta * (ann_rb - risk_free_rate))

    # Tracking Error = std(Rp - Rb) * sqrt(252)
    excess_returns = [rp[i] - rb[i] for i in range(n)]
    te = _std(excess_returns) * math.sqrt(252)

    # Information Ratio = (Rp - Rb) / TE (年化超额收益 / 年化跟踪误差)
    ir = ((mean_rp - mean_rb) * 252) / te if te > 0 else 0.0

    # 基准收益率
    bench_total_return = (bench_values[-1] / bench_values[0] - 1) * 100
    bench_annual_return = ((bench_values[-1] / bench_values[0]) ** (1 / max(years, 0.01)) - 1) * 100

    # 超额年化收益
    excess_annual = annual_return_excess = ann_rp - ann_rb

    return {
        "基准总收益率": f"{bench_total_return:+.2f}%",
        "基准年化收益率": f"{bench_annual_return:+.2f}%",
        "超额年化收益": f"{excess_annual*100:+.2f}%",
        "Alpha(年化)": f"{alpha*100:+.2f}%",
        "Beta": round(beta, 3),
        "跟踪误差(年化)": f"{te*100:.2f}%",
        "信息比率(IR)": round(ir, 2),
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


def _calc_sharpe_and_sortino(daily_returns: List[float], years: float,
                             risk_free_rate: float = 0.02) -> tuple:
    """计算夏普比率和索提诺比率 (无风险利率可配置)"""
    if not daily_returns:
        return 0.0, 0.0

    mean_ret = sum(daily_returns) / len(daily_returns)
    ann_mean = mean_ret * 252
    ann_std = _std(daily_returns) * math.sqrt(252)

    # 夏普: (年化收益 - 无风险利率) / 年化波动
    sharpe = (ann_mean - risk_free_rate) / ann_std if ann_std > 0 else 0.0

    # 索提诺 (只用下行波动)
    downside = [r for r in daily_returns if r < 0]
    if downside and len(downside) >= 2:
        d_std = _std(downside) * math.sqrt(252)
        sortino = (ann_mean - risk_free_rate) / d_std if d_std > 0 else 0.0
    else:
        sortino = 0.0

    return sharpe, sortino


def _std(values: List[float]) -> float:
    """样本标准差"""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def _variance(values: List[float]) -> float:
    """样本方差"""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / (len(values) - 1)


def _covariance(x: List[float], y: List[float]) -> float:
    """样本协方差"""
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    mean_x = sum(x[:n]) / n
    mean_y = sum(y[:n]) / n
    return sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / (n - 1)
