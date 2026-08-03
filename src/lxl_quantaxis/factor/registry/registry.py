"""Immutable factor registry keyed by identity and semantic version."""

from __future__ import annotations

from dataclasses import dataclass

from src.lxl_quantaxis.factor.base import FactorSpec


@dataclass(frozen=True, slots=True)
class FactorRegistry:
    specs: tuple[FactorSpec, ...] = ()

    def register(self, spec: FactorSpec) -> FactorRegistry:
        if any(item.factor_id == spec.factor_id and item.version == spec.version for item in self.specs):
            raise ValueError(f"factor version already registered: {spec.factor_id}@{spec.version}")
        return FactorRegistry(tuple(sorted((*self.specs, spec), key=lambda item: (item.factor_id, item.version))))

    def get(self, factor_id: str, version: str | None = None) -> FactorSpec:
        matches = [item for item in self.specs if item.factor_id == factor_id]
        if version is not None:
            matches = [item for item in matches if item.version == version]
        if not matches:
            raise KeyError(f"unknown factor: {factor_id}@{version or 'latest'}")
        return matches[-1]

    def list(self, category: str | None = None) -> tuple[FactorSpec, ...]:
        return tuple(item for item in self.specs if category is None or item.category.value == category)
