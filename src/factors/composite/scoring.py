"""
Factor Scoring — multi-factor composite scoring engine.

Combines multiple factor signals into a single composite score using
configurable weighting schemes:
  - equal_weight: All factors weighted equally
  - custom_weight: User-specified weights per factor
  - ic_weight: Weights proportional to each factor's Information Coefficient
  - rank_weight: Weights based on factor value percentile ranks

Usage:
    scorer = FactorScoring(data)
    composite = scorer.compute(
        factors=["momentum_score", "trend_strength", "volume_ratio"],
        scheme="equal_weight"
    )
"""

from typing import List, Dict, Optional
import pandas as pd
import numpy as np


class FactorScoring:
    """
    Multi-factor scoring engine.

    Computes weighted composite scores from multiple factor signals.
    """

    def __init__(self, data: pd.DataFrame):
        """
        Args:
            data: OHLCV DataFrame with standard columns.
        """
        self.data = data.copy()
        self._factor_cache: Dict[str, pd.Series] = {}

    # ---- Core computation ----

    def compute(self, factors: List[str],
                weights: Dict[str, float] = None,
                scheme: str = "equal_weight") -> pd.Series:
        """
        Compute a composite factor score.

        Args:
            factors: List of factor names to include.
            weights: Optional {factor_name: weight} dict for custom weighting.
            scheme: Weighting scheme — "equal_weight", "custom_weight",
                    "ic_weight", or "rank_weight".

        Returns:
            pd.Series of composite scores, normalized to 0–1.
        """
        if not factors:
            return pd.Series(0.5, index=self.data.index)

        # Resolve factor values
        factor_vals = {}
        for name in factors:
            series = self._resolve_factor(name)
            if series is not None:
                factor_vals[name] = series

        if not factor_vals:
            return pd.Series(0.5, index=self.data.index)

        # Determine weights
        w = self._resolve_weights(list(factor_vals.keys()), weights, scheme)

        # Compute weighted composite
        composite = pd.Series(0.0, index=self.data.index)
        total_weight = 0.0

        for name, series in factor_vals.items():
            weight = w.get(name, 0.0)
            if weight <= 0:
                continue
            # Normalize each factor to 0-1 before combining
            norm_series = self._normalize_series(series)
            composite = composite.add(norm_series * weight, fill_value=0)
            total_weight += weight

        if total_weight > 0:
            composite = composite / total_weight

        return composite.clip(0, 1)

    # ---- Ranking ----

    def rank_factors(self, factors: List[str]) -> pd.DataFrame:
        """
        Rank factors by recent signal strength.

        Returns DataFrame with columns: factor, latest_value, signal, rank.
        """
        rows = []
        for name in factors:
            series = self._resolve_factor(name)
            if series is not None and len(series.dropna()) > 0:
                latest = float(series.dropna().iloc[-1])
                signal = "bullish" if latest > 0.6 else ("bearish" if latest < 0.4 else "neutral")
                rows.append({
                    "factor": name,
                    "latest_value": round(latest, 4),
                    "signal": signal,
                })

        df = pd.DataFrame(rows)
        if "latest_value" in df.columns:
            df["rank"] = df["latest_value"].rank(ascending=False)
        return df.sort_values("rank") if "rank" in df.columns else df

    # ---- Helpers ----

    def _resolve_factor(self, name: str) -> Optional[pd.Series]:
        """Get factor values by name."""
        if name in self._factor_cache:
            return self._factor_cache[name]

        # Try registry first
        try:
            from src.factors.core.registry import registry
            registry.initialize_from_legacy()
            factor = registry.get(name)
            if factor is not None:
                series = factor.calculate(self.data)
                self._factor_cache[name] = series
                return series
        except Exception:
            pass

        # Fallback: FactorCalculator
        try:
            from src.factors.definitions import FactorCalculator
            calc = FactorCalculator(self.data)
            df = calc.compute_all()
            if name in df.columns:
                series = df[name]
                self._factor_cache[name] = series
                return series
        except Exception:
            pass

        return None

    def _resolve_weights(self, factor_names: List[str],
                         user_weights: Dict[str, float] = None,
                         scheme: str = "equal_weight") -> Dict[str, float]:
        """Determine factor weights based on scheme."""
        n = len(factor_names)

        if scheme == "custom_weight" and user_weights:
            return {k: user_weights.get(k, 1.0) for k in factor_names}

        if scheme == "ic_weight":
            # Weight by absolute IC from evaluator
            try:
                from src.factors.core.evaluator import FactorEvaluator
                evaluator = FactorEvaluator(self.data)
                w = {}
                for name in factor_names:
                    result = evaluator.evaluate(name)
                    w[name] = abs(result.get("IC", 0.01)) + 0.01  # Floor at 0.01
                return w
            except Exception:
                pass

        if scheme == "rank_weight":
            # Weight by signal extremity (distance from 0.5)
            w = {}
            for name in factor_names:
                series = self._resolve_factor(name)
                if series is not None and len(series.dropna()) > 0:
                    latest = series.dropna().iloc[-1]
                    w[name] = abs(latest - 0.5) * 2 + 0.1
                else:
                    w[name] = 0.1
            return w

        # Default: equal weight
        return {k: 1.0 for k in factor_names}

    @staticmethod
    def _normalize_series(series: pd.Series) -> pd.Series:
        """Ensure series is roughly 0–1 normalized."""
        if series.dropna().empty:
            return pd.Series(0.5, index=series.index)
        # Clip to sensible range
        q01 = series.quantile(0.01)
        q99 = series.quantile(0.99)
        if q99 - q01 > 0:
            return ((series - q01) / (q99 - q01)).clip(0, 1)
        return series.clip(0, 1)


def composite_score(data: pd.DataFrame, factors: List[str],
                    weights: Dict[str, float] = None) -> pd.Series:
    """
    Convenience function: compute a composite factor score.

    Args:
        data: OHLCV DataFrame.
        factors: List of factor names.
        weights: Optional {factor_name: weight} dict.

    Returns:
        pd.Series of 0–1 composite scores.
    """
    scorer = FactorScoring(data)
    scheme = "custom_weight" if weights else "equal_weight"
    return scorer.compute(factors, weights=weights, scheme=scheme)
