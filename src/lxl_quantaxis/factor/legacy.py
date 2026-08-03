"""Compatibility adapter for the existing FactorCalculator."""

from __future__ import annotations

import importlib
from typing import Any

from src.lxl_quantaxis.factor.base import FactorCategory, FactorSpec
from src.lxl_quantaxis.factor.registry import FactorRegistry

_CATEGORY_MAP = {
    "momentum": FactorCategory.MOMENTUM,
    "volatility": FactorCategory.VOLATILITY,
    "trend": FactorCategory.MOMENTUM,
    "volume": FactorCategory.QUALITY,
    "pattern": FactorCategory.SENTIMENT,
}


class LegacyFactorAdapter:
    def registry(self) -> FactorRegistry:
        definitions = importlib.import_module("src.factors.definitions")
        legacy_registry = definitions.FACTOR_REGISTRY

        registry = FactorRegistry()
        for name, legacy in legacy_registry.items():
            lookback = max((value for value in legacy.params.values() if isinstance(value, int)), default=1)
            registry = registry.register(
                FactorSpec(
                    factor_id=f"legacy.{name}",
                    version="1.0.0",
                    category=_CATEGORY_MAP.get(legacy.category, FactorCategory.QUALITY),
                    description=legacy.description,
                    lookback=lookback,
                    availability_lag=1,
                )
            )
        return registry

    def compute(self, name: str, data: Any) -> Any:
        definitions = importlib.import_module("src.factors.definitions")
        factors = definitions.FactorCalculator(data).compute_all()
        if name not in factors:
            raise KeyError(f"unknown legacy factor: {name}")
        return factors[name]
