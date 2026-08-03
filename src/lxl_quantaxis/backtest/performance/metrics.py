"""Pure numeric portfolio performance calculations."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    initial_capital: float
    final_equity: float
    total_return: float
    annual_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_start: str
    max_drawdown_end: str
    calmar_ratio: float
    trade_count: int
    closed_trade_count: int
    wins: int
    losses: int
    max_consecutive_losses: int
    win_rate: float
    average_win: float
    average_loss: float
    payoff_ratio: float
    profit_factor: float


def calculate_performance(
    daily_values: Sequence[Mapping[str, object]],
    trade_log: Sequence[Mapping[str, object]],
    initial_capital: float,
) -> PerformanceMetrics:
    if initial_capital <= 0 or not math.isfinite(initial_capital) or not daily_values:
        raise ValueError("performance requires positive capital and at least one valuation")
    values = [_as_float(item["total_value"], "total_value") for item in daily_values]
    dates = [str(item["date"]) for item in daily_values]
    if any(value <= 0 for value in values):
        raise ValueError("portfolio values must be positive")
    daily_returns = [current / previous - 1.0 for previous, current in pairwise(values)]
    years = len(values) / 252.0
    total_return = values[-1] / initial_capital - 1.0
    annual_return = (values[-1] / initial_capital) ** (1.0 / max(years, 0.01)) - 1.0
    max_drawdown, drawdown_start, drawdown_end = _drawdown(values, dates)
    sharpe, sortino = _risk_adjusted(daily_returns)
    closed = [item for item in trade_log if item.get("action") in {"SELL", "COVER"} and "pnl" in item]
    pnl = [_as_float(item["pnl"], "pnl") for item in closed]
    wins = [value for value in pnl if value > 0]
    losses = [value for value in pnl if value <= 0]
    average_win = sum(wins) / len(wins) if wins else 0.0
    average_loss = sum(losses) / len(losses) if losses else 0.0
    gross_loss = abs(sum(losses))
    profit_factor = sum(wins) / gross_loss if gross_loss else math.inf
    payoff_ratio = abs(average_win / average_loss) if average_loss else math.inf
    return PerformanceMetrics(
        initial_capital=initial_capital,
        final_equity=values[-1],
        total_return=total_return,
        annual_return=annual_return,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown=max_drawdown,
        max_drawdown_start=drawdown_start,
        max_drawdown_end=drawdown_end,
        calmar_ratio=annual_return / abs(max_drawdown) if max_drawdown else 0.0,
        trade_count=len(trade_log),
        closed_trade_count=len(closed),
        wins=len(wins),
        losses=len(losses),
        max_consecutive_losses=_loss_streak(pnl),
        win_rate=len(wins) / len(closed) if closed else 0.0,
        average_win=average_win,
        average_loss=average_loss,
        payoff_ratio=payoff_ratio,
        profit_factor=profit_factor,
    )


def _drawdown(values: list[float], dates: list[str]) -> tuple[float, str, str]:
    peak = values[0]
    peak_date = dates[0]
    minimum = 0.0
    start = dates[0]
    end = dates[0]
    for value, date in zip(values, dates, strict=True):
        if value > peak:
            peak = value
            peak_date = date
        drawdown = value / peak - 1.0
        if drawdown < minimum:
            minimum = drawdown
            start = peak_date
            end = date
    return minimum, start, end


def _risk_adjusted(returns: list[float]) -> tuple[float, float]:
    if len(returns) < 2:
        return 0.0, 0.0
    mean = sum(returns) / len(returns)
    annual_excess = mean * 252.0 - 0.02
    deviation = _sample_deviation(returns) * math.sqrt(252.0)
    downside = [value for value in returns if value < 0]
    downside_deviation = _sample_deviation(downside) * math.sqrt(252.0)
    return (
        annual_excess / deviation if deviation else 0.0,
        annual_excess / downside_deviation if downside_deviation else 0.0,
    )


def _sample_deviation(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _loss_streak(pnl: list[float]) -> int:
    maximum = 0
    current = 0
    for value in pnl:
        current = current + 1 if value <= 0 else 0
        maximum = max(maximum, current)
    return maximum


def _as_float(value: object, name: str) -> float:
    if not isinstance(value, (str, int, float, Decimal)) or isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result
