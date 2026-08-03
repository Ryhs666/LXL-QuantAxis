"""Immutable registry for strategy contracts and optional runtime factories."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol, TypeAlias

from src.lxl_quantaxis.strategy.base import ParameterValue, StrategySpec


class StrategyPlugin(Protocol):
    def buy_signal(self, data: object) -> bool: ...

    def sell_signal(self, data: object) -> bool: ...

    def on_bar(self, i: int, data: object, portfolio: object) -> object | None: ...


StrategyFactory: TypeAlias = Callable[..., StrategyPlugin]


@dataclass(frozen=True, slots=True)
class StrategyRegistration:
    spec: StrategySpec
    factory: StrategyFactory | None = None


@dataclass(frozen=True, slots=True)
class StrategyRegistry:
    registrations: tuple[StrategyRegistration, ...] = ()

    def register(self, spec: StrategySpec, factory: StrategyFactory | None = None) -> StrategyRegistry:
        if any(item.spec.identity == spec.identity for item in self.registrations):
            raise ValueError(f"strategy version already registered: {spec.identity}")
        registration = StrategyRegistration(spec, factory)
        return StrategyRegistry(
            tuple(
                sorted(
                    (*self.registrations, registration),
                    key=lambda item: (item.spec.strategy_id, _version_key(item.spec.version)),
                )
            )
        )

    def get(self, strategy_id: str, version: str | None = None) -> StrategySpec:
        return self._registration(strategy_id, version).spec

    def create(
        self,
        strategy_id: str,
        parameters: Mapping[str, object] | None = None,
        *,
        version: str | None = None,
        runtime_options: Mapping[str, object] | None = None,
    ) -> StrategyPlugin:
        registration = self._registration(strategy_id, version)
        validated: Mapping[str, ParameterValue] = registration.spec.validate_parameters(dict(parameters or {}))
        if registration.factory is None:
            raise ValueError(f"strategy has no runtime factory: {registration.spec.identity}")
        options = dict(runtime_options or {})
        overlap = set(validated) & set(options)
        if overlap:
            raise ValueError(f"runtime option conflicts with parameter(s): {', '.join(sorted(overlap))}")
        return registration.factory(**validated, **options)

    def list(self) -> tuple[StrategySpec, ...]:
        return tuple(item.spec for item in self.registrations)

    def _registration(self, strategy_id: str, version: str | None) -> StrategyRegistration:
        matches = [item for item in self.registrations if item.spec.strategy_id == strategy_id]
        if version is not None:
            matches = [item for item in matches if item.spec.version == version]
        if not matches:
            raise KeyError(f"unknown strategy: {strategy_id}@{version or 'latest'}")
        return matches[-1]


def _version_key(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)
