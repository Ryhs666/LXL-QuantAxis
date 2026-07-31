"""
Factor Evaluator — institutional-grade factor performance assessment.

Computes:
  - IC (Information Coefficient) — Pearson correlation between factor value and forward return
  - Rank IC — Spearman rank correlation
  - Return Correlation — time-series correlation with 1-day forward return
  - Signal Distribution — quantile-based signal spread analysis
  - Factor Decay — IC decay over holding periods

Usage:
    evaluator = FactorEvaluator(data)
    result = evaluator.evaluate("momentum_20")
    # → {"IC": 0.08, "Rank_IC": 0.12, "correlation": 0.15, ...}

    # Evaluate all registered factors
    df = evaluator.evaluate_all()
"""

from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np


class FactorEvaluator:
    """
    Evaluate factor performance against forward returns.

    Parameters:
        data: OHLCV DataFrame with standard columns.
        forward_periods: List of holding periods (in bars) for IC computation.
    """

    def __init__(self, data: pd.DataFrame, forward_periods: List[int] = None):
        self.data = data.copy()
        self.forward_periods = forward_periods or [1, 5, 10, 20]
        self._returns: Optional[pd.DataFrame] = None

    # ---- Forward returns ----

    def _compute_forward_returns(self) -> pd.DataFrame:
        """Compute forward returns for all holding periods."""
        if self._returns is not None:
            return self._returns

        close = self.data["close"]
        rets = pd.DataFrame(index=self.data.index)

        for period in self.forward_periods:
            rets[f"fwd_ret_{period}d"] = close.pct_change(period).shift(-period)

        rets["fwd_ret_1d"] = close.pct_change().shift(-1)
        self._returns = rets
        return rets

    # ---- Core evaluation ----

    def evaluate(self, factor: Any, factor_name: str = None) -> Dict[str, Any]:
        """
        Evaluate a single factor.

        Args:
            factor: Either a factor name (str) to look up in the registry,
                    a BaseFactor instance, or a pd.Series of factor values.
            factor_name: Optional display name (required if factor is a Series).

        Returns:
            Dict with keys: IC, Rank_IC, correlation, signal_distribution, etc.
        """
        # Resolve factor to a Series
        if isinstance(factor, str):
            factor_name = factor
            factor_values = self._resolve_factor_from_registry(factor)
        elif isinstance(factor, pd.Series):
            factor_values = factor
        else:
            # Assume BaseFactor instance
            factor_name = factor_name or factor.name
            factor_values = factor.calculate(self.data)

        if factor_values is None or factor_values.dropna().empty:
            return self._empty_result(factor_name or "unknown")

        # Align with returns
        fwd_rets = self._compute_forward_returns()
        common_idx = factor_values.dropna().index.intersection(
            fwd_rets["fwd_ret_1d"].dropna().index
        )

        if len(common_idx) < 30:
            return self._empty_result(factor_name or "unknown", "Insufficient data (< 30 obs)")

        fv = factor_values.loc[common_idx]
        fwd = fwd_rets["fwd_ret_1d"].loc[common_idx]

        # IC (Pearson)
        ic = fv.corr(fwd)
        ic = round(float(ic), 4) if not np.isnan(ic) else 0.0

        # Rank IC (Spearman)
        try:
            rank_ic = fv.rank().corr(fwd.rank())
            rank_ic = round(float(rank_ic), 4) if not np.isnan(rank_ic) else 0.0
        except Exception:
            rank_ic = 0.0

        # Return correlation (time-series)
        corr = round(float(ic), 4)

        # Signal distribution by quantile
        signal_dist = self._signal_distribution(fv)

        # IC decay across holding periods
        ic_decay = self._ic_decay(factor_values, fwd_rets, common_idx)

        # Rolling IC (12-month)
        rolling_ic = self._rolling_ic(fv, fwd, window=60)

        return {
            "factor": factor_name,
            "IC": ic,
            "Rank_IC": rank_ic,
            "correlation": corr,
            "signal_distribution": signal_dist,
            "ic_decay": ic_decay,
            "rolling_ic_mean": rolling_ic.get("mean", 0.0),
            "rolling_ic_std": rolling_ic.get("std", 0.0),
            "observations": len(common_idx),
        }

    def evaluate_all(self) -> pd.DataFrame:
        """Evaluate all registered factors and return a ranked DataFrame."""
        try:
            from src.factors.core.registry import registry
            registry.initialize_from_legacy()
            factor_names = registry.list_factors()
        except Exception:
            factor_names = []

        if not factor_names:
            return pd.DataFrame()

        results = []
        for name in factor_names:
            result = self.evaluate(name)
            results.append(result)

        df = pd.DataFrame(results)
        if "IC" in df.columns:
            df = df.sort_values("IC", ascending=False, key=abs)
        return df.reset_index(drop=True)

    # ---- Helpers ----

    def _resolve_factor_from_registry(self, name: str) -> Optional[pd.Series]:
        """Look up a factor in the registry and compute its values."""
        try:
            from src.factors.core.registry import registry
            registry.initialize_from_legacy()
            factor = registry.get(name)
            if factor is not None:
                return factor.calculate(self.data)
        except Exception:
            pass

        # Fallback: try using FactorCalculator directly
        try:
            from src.factors.definitions import FactorCalculator
            calc = FactorCalculator(self.data)
            factors_df = calc.compute_all()
            if name in factors_df.columns:
                return factors_df[name]
        except Exception:
            pass

        return None

    def _signal_distribution(self, factor_values: pd.Series) -> Dict[str, float]:
        """Compute quantile-based signal distribution."""
        fv = factor_values.dropna()
        if len(fv) < 10:
            return {"q10": 0, "q25": 0, "q50": 0, "q75": 0, "q90": 0}

        return {
            "q10": round(float(fv.quantile(0.10)), 4),
            "q25": round(float(fv.quantile(0.25)), 4),
            "q50": round(float(fv.quantile(0.50)), 4),
            "q75": round(float(fv.quantile(0.75)), 4),
            "q90": round(float(fv.quantile(0.90)), 4),
            "mean": round(float(fv.mean()), 4),
            "std": round(float(fv.std()), 4),
        }

    def _ic_decay(self, factor_values: pd.Series,
                  fwd_rets: pd.DataFrame,
                  common_idx: pd.Index) -> Dict[str, float]:
        """Compute IC across multiple holding periods."""
        decay = {}
        for period in self.forward_periods:
            col = f"fwd_ret_{period}d"
            if col not in fwd_rets.columns:
                continue
            ret = fwd_rets[col].dropna()
            idx = factor_values.dropna().index.intersection(ret.index)
            if len(idx) < 30:
                decay[f"IC_{period}d"] = 0.0
            else:
                ic = factor_values.loc[idx].corr(ret.loc[idx])
                decay[f"IC_{period}d"] = round(float(ic), 4) if not np.isnan(ic) else 0.0
        return decay

    def _rolling_ic(self, fv: pd.Series, fwd: pd.Series,
                    window: int = 60) -> Dict[str, float]:
        """Compute rolling IC statistics."""
        if len(fv) < window:
            return {"mean": 0.0, "std": 0.0}
        rolling = fv.rolling(window).corr(fwd)
        return {
            "mean": round(float(rolling.mean()), 4),
            "std": round(float(rolling.std()), 4),
        }

    @staticmethod
    def _empty_result(name: str, reason: str = "No data") -> Dict[str, Any]:
        return {
            "factor": name,
            "IC": 0.0,
            "Rank_IC": 0.0,
            "correlation": 0.0,
            "signal_distribution": {},
            "ic_decay": {},
            "rolling_ic_mean": 0.0,
            "rolling_ic_std": 0.0,
            "observations": 0,
            "error": reason,
        }


# --- Convenience functions ---

def evaluate_factor(factor: Any, data: pd.DataFrame,
                    factor_name: str = None) -> Dict[str, Any]:
    """
    Evaluate a single factor.

    Args:
        factor: Factor name (str), BaseFactor instance, or pd.Series.
        data: OHLCV DataFrame.
        factor_name: Optional name (required if factor is a Series).

    Returns:
        Dict with IC, Rank_IC, correlation, signal_distribution, etc.
    """
    evaluator = FactorEvaluator(data)
    return evaluator.evaluate(factor, factor_name=factor_name)


def evaluate_all_factors(data: pd.DataFrame) -> pd.DataFrame:
    """
    Evaluate all registered factors.

    Returns:
        DataFrame sorted by absolute IC, descending.
    """
    evaluator = FactorEvaluator(data)
    return evaluator.evaluate_all()
