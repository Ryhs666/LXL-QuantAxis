"""Immutable, versioned strategy specifications."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import TypeAlias, cast

ParameterValue: TypeAlias = str | int | float | bool


class ParameterType(StrEnum):
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    STRING = "string"


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    name: str
    kind: ParameterType
    default: ParameterValue
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[ParameterValue, ...] = ()

    def __post_init__(self) -> None:
        if re.fullmatch(r"[a-z][a-z0-9_]*", self.name) is None or self.name.startswith("_"):
            raise ValueError("parameter name must be a safe lowercase identifier")
        if not isinstance(self.kind, ParameterType):
            object.__setattr__(self, "kind", ParameterType(self.kind))
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("parameter minimum cannot exceed maximum")
        self.validate(self.default)

    def validate(self, value: object) -> ParameterValue:
        if self.kind is ParameterType.BOOLEAN:
            valid = isinstance(value, bool)
        elif self.kind is ParameterType.INTEGER:
            valid = isinstance(value, int) and not isinstance(value, bool)
        elif self.kind is ParameterType.NUMBER:
            valid = isinstance(value, (int, float)) and not isinstance(value, bool)
        else:
            valid = isinstance(value, str)
        if not valid:
            raise ValueError(f"parameter {self.name} must be {self.kind.value}")
        typed_value = cast(ParameterValue, value)
        if isinstance(typed_value, (int, float)) and not isinstance(typed_value, bool):
            if not isfinite(typed_value):
                raise ValueError(f"parameter {self.name} must be finite")
            if self.minimum is not None and typed_value < self.minimum:
                raise ValueError(f"parameter {self.name} is below its minimum")
            if self.maximum is not None and typed_value > self.maximum:
                raise ValueError(f"parameter {self.name} is above its maximum")
        if self.choices and typed_value not in self.choices:
            raise ValueError(f"parameter {self.name} is not an allowed choice")
        return typed_value


@dataclass(frozen=True, slots=True)
class StrategySpec:
    strategy_id: str
    version: str
    name: str
    description: str
    entry_rule: str
    exit_rule: str
    parameters: tuple[ParameterSpec, ...] = ()
    data_requirements: tuple[str, ...] = ("close",)
    source: str = "manual"

    def __post_init__(self) -> None:
        if re.fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)+", self.strategy_id) is None:
            raise ValueError("strategy_id must be a lowercase namespaced identifier")
        if re.fullmatch(r"\d+\.\d+\.\d+", self.version) is None:
            raise ValueError("strategy version must use major.minor.patch")
        if not self.name.strip() or not self.description.strip():
            raise ValueError("strategy name and description cannot be empty")
        if not isinstance(self.entry_rule, str) or not isinstance(self.exit_rule, str):
            raise ValueError("strategy rules must be strings")
        if len({item.name for item in self.parameters}) != len(self.parameters):
            raise ValueError("strategy parameter names must be unique")
        if not self.data_requirements or any(
            re.fullmatch(r"[a-z][a-z0-9_]*", item) is None or item.startswith("_") for item in self.data_requirements
        ):
            raise ValueError("data requirements must be safe identifiers")
        if len(set(self.data_requirements)) != len(self.data_requirements):
            raise ValueError("data requirements must be unique")
        if self.source not in {"manual", "ai", "legacy"}:
            raise ValueError("strategy source must be manual, ai, or legacy")

    @property
    def identity(self) -> str:
        return f"{self.strategy_id}@{self.version}"

    def validate_parameters(self, values: dict[str, object] | None = None) -> MappingProxyType[str, ParameterValue]:
        supplied = values or {}
        known = {item.name: item for item in self.parameters}
        unknown = set(supplied) - set(known)
        if unknown:
            raise ValueError(f"unknown strategy parameter(s): {', '.join(sorted(unknown))}")
        validated = {name: spec.validate(supplied.get(name, spec.default)) for name, spec in known.items()}
        return MappingProxyType(validated)

    def to_manifest(self) -> dict[str, object]:
        return {
            "strategy_id": self.strategy_id,
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "data_requirements": list(self.data_requirements),
            "parameters": [
                {
                    "name": item.name,
                    "type": item.kind.value,
                    "default": item.default,
                    "minimum": item.minimum,
                    "maximum": item.maximum,
                    "choices": list(item.choices),
                }
                for item in self.parameters
            ],
            "rules": {"entry": self.entry_rule, "exit": self.exit_rule},
        }
