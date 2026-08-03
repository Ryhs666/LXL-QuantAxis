"""Immutable, versioned factor specifications."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class FactorCategory(StrEnum):
    MOMENTUM = "momentum"
    VALUE = "value"
    QUALITY = "quality"
    VOLATILITY = "volatility"
    SENTIMENT = "sentiment"


@dataclass(frozen=True, slots=True)
class FactorSpec:
    factor_id: str
    version: str
    category: FactorCategory
    description: str
    lookback: int
    availability_lag: int
    higher_is_better: bool = True

    def __post_init__(self) -> None:
        if re.fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)+", self.factor_id) is None:
            raise ValueError("factor_id must be a lowercase namespaced identifier")
        if re.fullmatch(r"\d+\.\d+\.\d+", self.version) is None:
            raise ValueError("factor version must use major.minor.patch")
        if not isinstance(self.category, FactorCategory):
            object.__setattr__(self, "category", FactorCategory(self.category))
        if not self.description.strip():
            raise ValueError("factor description cannot be empty")
        if self.lookback < 1:
            raise ValueError("factor lookback must be positive")
        if self.availability_lag < 0:
            raise ValueError("factor availability_lag cannot be negative")
