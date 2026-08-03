"""Side-effect-free typed settings for the V2 core."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.lxl_quantaxis.core.contracts import validate_currency


class CoreConfigurationError(ValueError):
    """Raised when V2 core configuration is invalid."""


class RuntimeEnvironment(StrEnum):
    """Supported runtime environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


def _parse_bool(value: object, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise CoreConfigurationError(f"{name} must be true or false")


def _parse_environment(value: object) -> RuntimeEnvironment:
    if isinstance(value, RuntimeEnvironment):
        return value
    if not isinstance(value, str):
        raise CoreConfigurationError("environment must be a string")
    aliases = {"dev": "development", "prod": "production", "testing": "test"}
    normalized = aliases.get(value.strip().lower(), value.strip().lower())
    try:
        return RuntimeEnvironment(normalized)
    except ValueError as exc:
        raise CoreConfigurationError(f"unsupported environment: {value!r}") from exc


def _parse_timezone(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CoreConfigurationError("timezone must be a non-empty IANA timezone name")
    normalized = value.strip()
    try:
        ZoneInfo(normalized)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise CoreConfigurationError(f"unknown IANA timezone: {normalized!r}") from exc
    return normalized


def _parse_currency(value: object) -> str:
    try:
        return validate_currency(value)
    except ValueError as exc:
        raise CoreConfigurationError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class CoreSettings:
    """Configuration loaded by explicit precedence without I/O side effects."""

    enabled: bool = False
    environment: RuntimeEnvironment = RuntimeEnvironment.DEVELOPMENT
    timezone_name: str = "Asia/Shanghai"
    default_currency: str = "CNY"

    def __post_init__(self) -> None:
        object.__setattr__(self, "enabled", _parse_bool(self.enabled, "enabled"))
        object.__setattr__(self, "environment", _parse_environment(self.environment))
        object.__setattr__(self, "timezone_name", _parse_timezone(self.timezone_name))
        object.__setattr__(self, "default_currency", _parse_currency(self.default_currency))

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    @classmethod
    def from_sources(
        cls,
        *,
        legacy: Mapping[str, object] | None = None,
        environ: Mapping[str, str] | None = None,
        overrides: Mapping[str, object] | None = None,
    ) -> CoreSettings:
        """Load defaults < legacy < environment < explicit overrides."""

        values: dict[str, object] = {
            "enabled": False,
            "environment": RuntimeEnvironment.DEVELOPMENT,
            "timezone_name": "Asia/Shanghai",
            "default_currency": "CNY",
        }
        aliases = {
            "enabled": "enabled",
            "v2_core_enabled": "enabled",
            "environment": "environment",
            "timezone": "timezone_name",
            "timezone_name": "timezone_name",
            "core_timezone": "timezone_name",
            "default_currency": "default_currency",
        }

        if legacy is not None:
            for source_name, target_name in aliases.items():
                if source_name in legacy:
                    values[target_name] = legacy[source_name]

        environment_source = os.environ if environ is None else environ
        environment_keys = {
            "V2_CORE_ENABLED": "enabled",
            "LXL_ENV": "environment",
            "LXL_TIMEZONE": "timezone_name",
            "LXL_DEFAULT_CURRENCY": "default_currency",
        }
        for source_name, target_name in environment_keys.items():
            if source_name in environment_source:
                values[target_name] = environment_source[source_name]

        if overrides is not None:
            unknown_keys = set(overrides) - set(aliases)
            if unknown_keys:
                unknown = ", ".join(sorted(unknown_keys))
                raise CoreConfigurationError(f"unknown core setting(s): {unknown}")
            for source_name, value in overrides.items():
                values[aliases[source_name]] = value

        return cls(
            enabled=_parse_bool(values["enabled"], "enabled"),
            environment=_parse_environment(values["environment"]),
            timezone_name=_parse_timezone(values["timezone_name"]),
            default_currency=_parse_currency(values["default_currency"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "environment": self.environment.value,
            "timezone": self.timezone_name,
            "default_currency": self.default_currency,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_json(cls, value: str) -> CoreSettings:
        try:
            payload = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise CoreConfigurationError("core settings must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise CoreConfigurationError("core settings JSON must contain an object")
        return cls.from_sources(environ={}, overrides=payload)
