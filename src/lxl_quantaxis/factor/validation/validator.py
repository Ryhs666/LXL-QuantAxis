"""Cross-sectional factor validation metrics."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FactorValidationReport:
    ic_mean: float
    rank_ic_mean: float
    ic_decay: tuple[float, ...]
    turnover: float
    stability: float
    observations: int


class FactorValidator:
    def validate(
        self,
        factor: Any,
        forward_returns: Any,
        *,
        decay_horizons: tuple[int, ...] = (1, 5, 10),
    ) -> FactorValidationReport:
        importlib.import_module("pandas")
        aligned_factor, aligned_returns = factor.align(forward_returns, join="inner", axis=None)
        pearson = aligned_factor.corrwith(aligned_returns, axis=1).dropna()
        rank = aligned_factor.rank(axis=1, pct=True).corrwith(aligned_returns.rank(axis=1, pct=True), axis=1).dropna()
        decay: list[float] = []
        for horizon in decay_horizons:
            shifted = aligned_returns.shift(-max(horizon - 1, 0))
            values = aligned_factor.corrwith(shifted, axis=1).dropna()
            decay.append(float(values.mean()) if not values.empty else 0.0)
        ranks = aligned_factor.rank(axis=1, pct=True)
        turnover = float(ranks.diff().abs().mean(axis=1).dropna().mean())
        stability = float((pearson > 0).mean()) if not pearson.empty else 0.0
        return FactorValidationReport(
            ic_mean=float(pearson.mean()) if not pearson.empty else 0.0,
            rank_ic_mean=float(rank.mean()) if not rank.empty else 0.0,
            ic_decay=tuple(decay),
            turnover=turnover,
            stability=stability,
            observations=len(pearson),
        )
