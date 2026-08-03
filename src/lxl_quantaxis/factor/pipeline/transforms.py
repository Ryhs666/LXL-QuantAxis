"""Deterministic cross-sectional factor transformations."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FactorPipeline:
    availability_lag: int = 1
    winsor_limits: tuple[float, float] = (0.01, 0.99)
    neutralize_groups: Any | None = None
    standardize: bool = True

    def __post_init__(self) -> None:
        lower, upper = self.winsor_limits
        if self.availability_lag < 0:
            raise ValueError("availability_lag cannot be negative")
        if not 0 <= lower <= upper <= 1:
            raise ValueError("winsor limits must satisfy 0 <= lower <= upper <= 1")

    def transform(self, values: Any) -> Any:
        importlib.import_module("pandas")
        result = values.astype(float).shift(self.availability_lag)
        lower, upper = self.winsor_limits
        low_values = result.quantile(lower, axis=1)
        high_values = result.quantile(upper, axis=1)
        result = result.clip(lower=low_values, upper=high_values, axis=0)
        if self.neutralize_groups is not None:
            groups = self.neutralize_groups.reindex(result.columns)
            for group in groups.dropna().unique():
                columns = groups[groups == group].index
                result.loc[:, columns] = result.loc[:, columns].sub(result.loc[:, columns].mean(axis=1), axis=0)
        if self.standardize:
            mean = result.mean(axis=1)
            deviation = result.std(axis=1, ddof=0).replace(0, float("nan"))
            result = result.sub(mean, axis=0).div(deviation, axis=0)
        return result
