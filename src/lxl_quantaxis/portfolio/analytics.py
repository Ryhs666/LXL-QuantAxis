"""Portfolio return and risk analytics with explicit semantics.

All functions declare their expected return type (simple vs log) and
rebalance mode.  No silent coercion between types.

Validation is fail-fast: bad inputs raise immediately rather than
producing silently-wrong numbers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


import numpy as np
import pandas as pd


# ═══════════════════════════════════════════════════════════
# Explicit type enums
# ═══════════════════════════════════════════════════════════


class ReturnType(str, Enum):
    SIMPLE = "simple"   # pct_change:  r_t = (p_t / p_{t-1}) - 1
    LOG = "log"         # log return: r_t = ln(p_t / p_{t-1})


class RebalanceMode(str, Enum):
    PERIODIC = "periodic"        # reset to target weights each period
    BUY_AND_HOLD = "buy_and_hold"  # let weights drift with asset values


# ═══════════════════════════════════════════════════════════
# Input validation helpers
# ═══════════════════════════════════════════════════════════


def _validate_returns(
    returns: pd.Series | pd.DataFrame,
    return_type: ReturnType,
    min_obs: int = 1,
) -> None:
    if isinstance(returns, pd.DataFrame):
        for col in returns.columns:
            _validate_returns(returns[col], return_type, min_obs)
        return

    if not isinstance(returns, pd.Series):
        raise TypeError(f"returns must be Series or DataFrame, got {type(returns).__name__}")
    if len(returns) < min_obs:
        raise ValueError(f"need at least {min_obs} observations, got {len(returns)}")
    if returns.isna().any():
        raise ValueError("returns contain NaN values")
    if not np.isfinite(returns.values).all():
        raise ValueError("returns contain inf values")
    if (returns.index.duplicated()).any():
        raise ValueError("returns index contains duplicate dates")
    if not returns.index.is_monotonic_increasing:
        raise ValueError("returns index is not monotonically increasing")

    if return_type == ReturnType.SIMPLE and (returns < -1).any():
        raise ValueError("simple returns cannot be less than -1")


def _validate_weights(
    weights: pd.Series,
    tolerance: float = 1e-8,
    long_only: bool = True,
) -> None:
    if not isinstance(weights, pd.Series):
        raise TypeError(f"weights must be Series, got {type(weights).__name__}")
    if weights.isna().any():
        raise ValueError("weights contain NaN")
    if not np.isfinite(weights.values).all():
        raise ValueError("weights contain inf")
    if weights.index.duplicated().any():
        raise ValueError("weights index has duplicate entries")
    if long_only and (weights < 0).any():
        raise ValueError(f"long-only constraint violated: {weights[weights < 0].to_dict()}")
    total = weights.sum()
    if abs(total - 1.0) > tolerance:
        raise ValueError(f"weights sum to {total:.10f}, expected 1.0 (tolerance={tolerance})")


def _validate_periods_per_year(ppy: float) -> None:
    if not isinstance(ppy, (int, float)):
        raise TypeError(f"periods_per_year must be numeric, got {type(ppy).__name__}")
    if isinstance(ppy, bool):
        raise TypeError("periods_per_year must not be bool")
    if not np.isfinite(ppy) or ppy <= 0:
        raise ValueError(f"periods_per_year must be finite positive, got {ppy}")


# ═══════════════════════════════════════════════════════════
# Core metric functions
# ═══════════════════════════════════════════════════════════


def cumulative_return(returns: pd.Series, return_type: ReturnType) -> float:
    """Total compounded return.

    SIMPLE:  prod(1 + r) - 1
    LOG:     exp(sum(r)) - 1
    """
    _validate_returns(returns, return_type)
    if return_type == ReturnType.LOG:
        return float(np.exp(returns.sum()) - 1)
    return float(np.prod(1 + returns) - 1)


def annualized_return(
    returns: pd.Series,
    return_type: ReturnType,
    periods_per_year: float = 252,
) -> float:
    """Annualized compounded return."""
    _validate_returns(returns, return_type)
    _validate_periods_per_year(periods_per_year)
    cum = 1 + cumulative_return(returns, return_type)
    if cum <= 0:
        raise ValueError("cumulative value is non-positive, cannot annualize")
    n = len(returns)
    return float(cum ** (periods_per_year / n) - 1)


def annualized_volatility(
    returns: pd.Series,
    return_type: ReturnType,
    periods_per_year: float = 252,
) -> float:
    """Annualized volatility (sample std dev, ddof=1)."""
    _validate_returns(returns, return_type, min_obs=2)
    _validate_periods_per_year(periods_per_year)
    return float(returns.std(ddof=1) * np.sqrt(periods_per_year))


def sharpe_ratio(
    returns: pd.Series,
    return_type: ReturnType,
    risk_free_rate: float = 0.0,
    periods_per_year: float = 252,
) -> float | None:
    """Annualized Sharpe ratio.

    Returns None (not inf or misleading number) when volatility is
    effectively zero.
    """
    _validate_returns(returns, return_type, min_obs=2)
    _validate_periods_per_year(periods_per_year)
    if not isinstance(risk_free_rate, (int, float)) or isinstance(risk_free_rate, bool):
        raise TypeError("risk_free_rate must be numeric, not bool")
    if not np.isfinite(risk_free_rate) or risk_free_rate <= -1:
        raise ValueError(f"risk_free_rate must be finite and > -1, got {risk_free_rate}")

    rf_per_period = (1 + risk_free_rate) ** (1 / periods_per_year) - 1
    excess = returns - rf_per_period
    mean_excess = excess.mean()
    std_excess = excess.std(ddof=1)

    if np.isclose(std_excess, 0.0, atol=1e-12):
        return None  # Not misleading inf

    return float((mean_excess / std_excess) * np.sqrt(periods_per_year))


def max_drawdown(returns: pd.Series) -> float:
    """Maximum drawdown from peak (returns a non-positive number)."""
    _validate_returns(returns, ReturnType.SIMPLE)
    eq = np.concatenate([[1.0], (1 + returns).values])
    cum = np.cumprod(eq)
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / peak
    return float(min(dd.min(), 0.0))


def calmar_ratio(
    returns: pd.Series,
    return_type: ReturnType,
    periods_per_year: float = 252,
) -> float | None:
    """Annualized return / abs(max drawdown).  None when drawdown is zero."""
    ann_ret = annualized_return(returns, return_type, periods_per_year)
    dd = max_drawdown(returns)
    if abs(dd) < 1e-12:
        return None
    return float(ann_ret / abs(dd))


# ═══════════════════════════════════════════════════════════
# Portfolio-level aggregation
# ═══════════════════════════════════════════════════════════


def portfolio_return_series(
    returns: pd.DataFrame,
    weights: pd.Series,
    return_type: ReturnType = ReturnType.SIMPLE,
    rebalance_mode: RebalanceMode = RebalanceMode.PERIODIC,
    rebalance_cost_bps: float = 0.0,
) -> pd.Series:
    """Compute portfolio-level return series from asset returns and weights.

    PERIODIC: each period resets to target weights.
        portfolio_return[t] = sum(w_i * r_{i,t})

    BUY_AND_HOLD: start with target weights, let them drift with prices.
        weight[t] = weight[t-1] * (1 + return[t]) / sum(...)
        portfolio_return[t] = sum(weight[t] * return[t])

    Args:
        returns: DataFrame (dates x assets) of period returns
        weights: Series indexed by asset name, sum to 1
        return_type: SIMPLE or LOG
        rebalance_mode: PERIODIC or BUY_AND_HOLD
        rebalance_cost_bps: rebalance cost in basis points (0.0001 = 1bps)
            0 means "cost not modeled" — users are warned if this is
            non-zero but left at default.
    """
    _validate_returns(returns, return_type)
    _validate_weights(weights)

    # Align columns
    missing = set(weights.index) - set(returns.columns)
    extra = set(returns.columns) - set(weights.index)
    if missing:
        raise ValueError(f"weights reference assets not in returns: {sorted(missing)}")
    if extra:
        raise ValueError(f"returns contain assets not in weights: {sorted(extra)}")
    aligned = returns[weights.index.tolist()]

    if return_type == ReturnType.LOG:
        raise NotImplementedError(
            "Log-return portfolio aggregation is ambiguous for multi-asset. "
            "Convert to simple returns first, or use single-asset path."
        )

    if rebalance_mode == RebalanceMode.PERIODIC:
        port = aligned.dot(weights)
        port.name = "portfolio_return"
        return port

    # BUY_AND_HOLD: weights drift with price changes
    w = weights.values.copy()
    port_rets = []
    for i in range(len(aligned)):
        asset_rets = aligned.iloc[i].values
        port_ret = np.dot(w, asset_rets)
        port_rets.append(port_ret)
        w = w * (1 + asset_rets)
        w = w / w.sum()

        if rebalance_cost_bps > 0:
            # Subtract turnover cost (simplified: proportional to weight change)
            turnover = np.abs(w - weights.values).sum() / 2
            cost = turnover * rebalance_cost_bps / 10000
            port_rets[-1] -= cost

    result = pd.Series(port_rets, index=aligned.index, name="portfolio_return")
    return result


# ═══════════════════════════════════════════════════════════
# Immutable result object
# ═══════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class PortfolioMetrics:
    total_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float | None
    max_drawdown: float
    calmar_ratio: float | None
    observation_count: int
    return_type: ReturnType
    rebalance_mode: RebalanceMode | None = None

    def to_dict(self) -> dict:
        return {
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "annualized_volatility": self.annualized_volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "calmar_ratio": self.calmar_ratio,
            "observation_count": self.observation_count,
            "return_type": self.return_type.value,
            "rebalance_mode": self.rebalance_mode.value if self.rebalance_mode else None,
        }


def summarize(
    returns: pd.DataFrame,
    weights: pd.Series,
    return_type: ReturnType = ReturnType.SIMPLE,
    rebalance_mode: RebalanceMode = RebalanceMode.PERIODIC,
    risk_free_rate: float = 0.0,
    periods_per_year: float = 252,
) -> PortfolioMetrics:
    """One-shot portfolio metrics computation."""
    port_rets = portfolio_return_series(
        returns, weights, return_type=return_type, rebalance_mode=rebalance_mode,
    )
    return PortfolioMetrics(
        total_return=cumulative_return(port_rets, ReturnType.SIMPLE),
        annualized_return=annualized_return(port_rets, ReturnType.SIMPLE, periods_per_year),
        annualized_volatility=annualized_volatility(port_rets, ReturnType.SIMPLE, periods_per_year),
        sharpe_ratio=sharpe_ratio(port_rets, ReturnType.SIMPLE, risk_free_rate, periods_per_year),
        max_drawdown=max_drawdown(port_rets),
        calmar_ratio=calmar_ratio(port_rets, ReturnType.SIMPLE, periods_per_year),
        observation_count=len(port_rets),
        return_type=return_type,
        rebalance_mode=rebalance_mode,
    )
