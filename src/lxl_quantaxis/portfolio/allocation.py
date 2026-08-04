"""Statistically valid portfolio allocation models.

All models accept a returns matrix (dates x assets) and output
long-only weights that sum to 1.  Walk-forward evaluation ensures
weights are never fit on test-period data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd


# ═══════════════════════════════════════════════════════════
# Input validation
# ═══════════════════════════════════════════════════════════


def _validate_returns_matrix(returns: pd.DataFrame, min_periods: int = 20) -> None:
    if not isinstance(returns, pd.DataFrame):
        raise TypeError(f"returns must be DataFrame, got {type(returns).__name__}")
    if returns.empty:
        raise ValueError("returns is empty")
    if len(returns) < min_periods:
        raise ValueError(f"need at least {min_periods} periods, got {len(returns)}")
    if returns.columns.duplicated().any():
        raise ValueError("duplicate column names in returns matrix")
    if not isinstance(returns.index, pd.DatetimeIndex):
        raise TypeError("returns index must be DatetimeIndex")
    if returns.index.duplicated().any():
        raise ValueError("duplicate dates in returns index")
    if not returns.index.is_monotonic_increasing:
        raise ValueError("returns index not monotonically increasing")
    if returns.isna().any().any():
        raise ValueError("returns contain NaN")
    if not returns.map(np.isfinite).all().all():
        raise ValueError("returns contain inf")


# ═══════════════════════════════════════════════════════════
# Allocation models
# ═══════════════════════════════════════════════════════════


def equal_weight(returns: pd.DataFrame) -> pd.Series:
    """Equal weight across all assets."""
    n = len(returns.columns)
    return pd.Series(1.0 / n, index=returns.columns, name="weight")


def inverse_volatility(returns: pd.DataFrame) -> pd.Series:
    """Inverse-volatility weighted (fallback when scipy unavailable)."""
    vols = returns.std(ddof=1)
    vols = vols.replace(0, np.nan)
    if vols.isna().any():
        return equal_weight(returns)
    inv = 1.0 / vols
    w = inv / inv.sum()
    w.name = "weight"
    return w


def risk_parity(returns: pd.DataFrame) -> pd.Series:
    """Long-only risk parity via scipy SLSQP.  Falls back to inverse-vol."""
    n = len(returns.columns)
    if n == 1:
        return pd.Series(1.0, index=returns.columns, name="weight")

    try:
        from scipy.optimize import minimize
    except ImportError:
        return inverse_volatility(returns)

    cov = returns.cov().values

    def _risk_budget_objective(w):
        w = np.array(w)
        pvar = w @ cov @ w
        mrc = cov @ w
        rc = w * mrc
        target = pvar / n
        return np.sum((rc - target) ** 2)

    result = minimize(
        _risk_budget_objective,
        np.ones(n) / n,
        method="SLSQP",
        bounds=[(0, 1)] * n,
        constraints=[{"type": "eq", "fun": lambda x: np.sum(x) - 1}],
        options={"maxiter": 2000, "ftol": 1e-12},
    )
    w = result.x if result.success else np.ones(n) / n
    return pd.Series(np.clip(w, 0, None) / w.sum(), index=returns.columns, name="weight")


def mean_variance(returns: pd.DataFrame, target_return: Optional[float] = None) -> pd.Series:
    """Long-only mean-variance.  Maximizes Sharpe if target_return is None."""
    n = len(returns.columns)
    if n == 1:
        return pd.Series(1.0, index=returns.columns, name="weight")

    try:
        from scipy.optimize import minimize
    except ImportError:
        return inverse_volatility(returns)

    cov = returns.cov().values
    mean = returns.mean().values

    if target_return is not None:
        def _risk_objective(w):
            return w @ cov @ w
        constraints = [
            {"type": "eq", "fun": lambda x: np.sum(x) - 1},
            {"type": "eq", "fun": lambda x: np.dot(x, mean) - target_return},
        ]
        result = minimize(_risk_objective, np.ones(n) / n, method="SLSQP",
                         bounds=[(0, 1)] * n, constraints=constraints,
                         options={"maxiter": 2000, "ftol": 1e-12})
        if not result.success:
            raise ValueError(f"target_return {target_return:.6f} is infeasible "
                             f"with long-only constraints")
    else:
        def _neg_sharpe(w):
            pr = np.dot(w, mean)
            pv = math.sqrt(max(w @ cov @ w, 1e-16))
            return -(pr / pv)
        result = minimize(_neg_sharpe, np.ones(n) / n, method="SLSQP",
                         bounds=[(0, 1)] * n,
                         constraints=[{"type": "eq", "fun": lambda x: np.sum(x) - 1}],
                         options={"maxiter": 2000, "ftol": 1e-12})

    w = result.x if result.success else np.ones(n) / n
    return pd.Series(np.clip(w, 0, None) / w.sum(), index=returns.columns, name="weight")


# ═══════════════════════════════════════════════════════════
# Hierarchical Risk Parity (true HRP)
# ═══════════════════════════════════════════════════════════


def hierarchical_risk_parity(returns: pd.DataFrame) -> pd.Series:
    """True HRP: cov→corr→distance→linkage→quasi-diagonalize→recursive bisection.

    If scipy is unavailable, falls back to inverse-volatility with a warning.
    """
    n = len(returns.columns)
    if n <= 2:
        return inverse_volatility(returns)

    try:
        from scipy.cluster.hierarchy import linkage
        from scipy.spatial.distance import squareform
    except ImportError:
        return inverse_volatility(returns)

    cov = returns.cov().values
    std = returns.std(ddof=1).values
    std_safe = np.where(std > 1e-12, std, 1.0)
    corr = np.clip(cov / np.outer(std_safe, std_safe), -1.0, 1.0)

    dist = np.sqrt(0.5 * (1.0 - corr))
    np.fill_diagonal(dist, 0.0)

    try:
        dist_cond = squareform(dist, checks=False)
        link = linkage(dist_cond, method="single")
    except Exception:
        return inverse_volatility(returns)

    # quasi-diagonalization: get leaf order
    clusters = {i: [i] for i in range(n)}
    next_id = n
    for row in link:
        left, right = int(row[0]), int(row[1])
        clusters[next_id] = clusters[left] + clusters[right]
        del clusters[left], clusters[right]
        next_id += 1

    order = clusters[max(clusters.keys())]
    ordered_cov = cov[order][:, order]

    def _bisect(c: np.ndarray) -> np.ndarray:
        m = c.shape[0]
        if m == 1:
            return np.array([1.0])
        s = m // 2
        lw = _bisect(c[:s, :s])
        rw = _bisect(c[s:, s:])
        lv = lw @ c[:s, :s] @ lw
        rv = rw @ c[s:, s:] @ rw
        if lv < 1e-16 and rv < 1e-16:
            al = 0.5
        elif lv < 1e-16:
            al = 0.0
        elif rv < 1e-16:
            al = 1.0
        else:
            al = (1.0 / lv) / (1.0 / lv + 1.0 / rv)
        res = np.zeros(m)
        res[:s] = al * lw
        res[s:] = (1.0 - al) * rw
        return res

    w_ordered = _bisect(ordered_cov)
    w = np.zeros(n)
    for i, orig in enumerate(order):
        w[orig] = w_ordered[i]
    w = w / w.sum()
    return pd.Series(w, index=returns.columns, name="weight")


# ═══════════════════════════════════════════════════════════
# Walk-forward evaluation
# ═══════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class WalkForwardWindow:
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    weights: dict[str, float]
    test_return: float
    test_volatility: float
    n_train: int
    n_test: int


def walk_forward(
    returns: pd.DataFrame,
    model: str = "risk_parity",
    train_window: int = 252,
    test_window: int = 63,
    target_return: Optional[float] = None,
) -> list[WalkForwardWindow]:
    """Walk-forward evaluation.

    For each window:
      1. Fit weights on train_window periods
      2. Apply weights to the next test_window periods
      3. Record test-period return
      4. Advance both windows by test_window

    The model NEVER sees test-period data during fitting.

    Args:
        returns: DataFrame (dates x assets) of period returns
        model: "equal", "risk_parity", "mean_variance"
        train_window: number of periods for training
        test_window: number of periods for testing
        target_return: only used with mean_variance model

    Returns:
        List of WalkForwardWindow records
    """
    _validate_returns_matrix(returns, min_periods=train_window + test_window)

    models = {
        "equal": equal_weight,
        "risk_parity": risk_parity,
        "mean_variance": mean_variance,
        "hrp": hierarchical_risk_parity,
    }
    fit_fn = models.get(model)
    if fit_fn is None:
        raise ValueError(f"unknown model: {model}, choose from {list(models)}")

    windows = []
    start = 0
    while start + train_window + test_window <= len(returns):
        train = returns.iloc[start:start + train_window]
        test = returns.iloc[start + train_window:start + train_window + test_window]

        kwargs = {}
        if model == "mean_variance" and target_return is not None:
            kwargs["target_return"] = target_return
        weights = fit_fn(train, **kwargs)
        weights = weights.reindex(returns.columns, fill_value=0.0)
        weights = weights / weights.sum()

        test_port_ret = test.dot(weights)
        test_ret = float((1 + test_port_ret).prod() - 1)
        test_vol = float(test_port_ret.std(ddof=1) * math.sqrt(252))

        windows.append(WalkForwardWindow(
            train_start=str(train.index[0])[:10],
            train_end=str(train.index[-1])[:10],
            test_start=str(test.index[0])[:10],
            test_end=str(test.index[-1])[:10],
            weights={str(k): round(float(v), 4) for k, v in weights.items()},
            test_return=round(test_ret, 6),
            test_volatility=round(test_vol, 6),
            n_train=len(train),
            n_test=len(test),
        ))
        start += test_window

    return windows


def walk_forward_summary(windows: list[WalkForwardWindow]) -> dict:
    """Aggregate walk-forward results."""
    if not windows:
        return {"error": "no windows"}
    rets = [w.test_return for w in windows]
    vols = [w.test_volatility for w in windows]
    return {
        "windows": len(windows),
        "mean_test_return": round(float(np.mean(rets)), 6),
        "mean_test_volatility": round(float(np.mean(vols)), 6),
        "total_test_return": round(float(np.prod([1 + r for r in rets]) - 1), 6),
        "sharpe": round(float(np.mean(rets) / max(np.std(rets, ddof=1), 1e-12) * math.sqrt(252 / len(windows))), 4) if len(rets) > 1 else None,
        "positive_windows": sum(1 for r in rets if r > 0),
        "model": "walk-forward (no look-ahead bias)",
    }
