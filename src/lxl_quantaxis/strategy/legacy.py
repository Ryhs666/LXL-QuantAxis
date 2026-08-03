"""Compatibility adapter for the existing strategy library."""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Mapping
from typing import Any

from src.lxl_quantaxis.strategy.base import ParameterSpec, ParameterType, StrategySpec
from src.lxl_quantaxis.strategy.registry import StrategyRegistry


def legacy_strategy_spec(key: str, definition: Mapping[str, Any]) -> StrategySpec:
    factory = definition.get("class")
    signature = inspect.signature(factory) if factory is not None else None
    parameters = tuple(
        _legacy_parameter(
            name,
            value,
            signature.parameters[name].default
            if signature is not None and name in signature.parameters
            else inspect.Parameter.empty,
        )
        for name, value in definition.get("params", {}).items()
    )
    return StrategySpec(
        strategy_id=f"legacy.{key}",
        version="1.0.0",
        name=str(definition.get("name") or key),
        description=str(definition.get("description") or f"Legacy strategy {key}"),
        entry_rule="",
        exit_rule="",
        parameters=parameters,
        data_requirements=("open", "high", "low", "close", "volume"),
        source="legacy",
    )


def get_legacy_strategy_registry() -> StrategyRegistry:
    module = importlib.import_module("src.strategies.library")
    definitions: Mapping[str, Mapping[str, Any]] = module.STRATEGIES
    registry = StrategyRegistry()
    for key, definition in definitions.items():
        factory = definition.get("class")
        if factory is not None:
            registry = registry.register(legacy_strategy_spec(key, definition), factory)
    return registry


def _legacy_parameter(name: str, value: object, declared_default: object = inspect.Parameter.empty) -> ParameterSpec:
    if isinstance(value, list) and value and all(isinstance(item, bool) for item in value):
        boolean_default = declared_default if isinstance(declared_default, bool) else value[0]
        return ParameterSpec(name, ParameterType.BOOLEAN, boolean_default, choices=tuple(value))
    if (
        isinstance(value, tuple)
        and len(value) == 2
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
    ):
        low, high = value
        kind = ParameterType.INTEGER if isinstance(low, int) and isinstance(high, int) else ParameterType.NUMBER
        numeric_default: int | float = (
            declared_default
            if isinstance(declared_default, (int, float)) and not isinstance(declared_default, bool)
            else low
        )
        return ParameterSpec(name, kind, numeric_default, minimum=float(low), maximum=float(high))
    if isinstance(value, bool):
        return ParameterSpec(name, ParameterType.BOOLEAN, value)
    if isinstance(value, int):
        return ParameterSpec(name, ParameterType.INTEGER, value)
    if isinstance(value, float):
        return ParameterSpec(name, ParameterType.NUMBER, value)
    return ParameterSpec(name, ParameterType.STRING, str(value))
