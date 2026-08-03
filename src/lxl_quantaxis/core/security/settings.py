"""Typed, fail-closed security settings for LXL-QuantAxis."""

from __future__ import annotations

import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field


class SecurityConfigurationError(RuntimeError):
    """Raised when security-sensitive configuration is unsafe."""


def _read_int(
    source: Mapping[str, str],
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw_value = source.get(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise SecurityConfigurationError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise SecurityConfigurationError(f"{name} must be between {minimum} and {maximum}")
    return value


def _read_bool(source: Mapping[str, str], name: str, default: bool) -> bool:
    raw_value = source.get(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise SecurityConfigurationError(f"{name} must be true or false")


@dataclass(frozen=True, slots=True)
class SecuritySettings:
    """Security settings loaded without framework or database side effects."""

    environment: str
    jwt_secret: str = field(repr=False)
    jwt_secret_is_ephemeral: bool
    bind_host: str
    access_token_expire_hours: int
    registration_enabled: bool
    auth_rate_limit_attempts: int
    auth_rate_limit_window_seconds: int

    @property
    def is_production(self) -> bool:
        return self.environment in {"prod", "production"}

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> SecuritySettings:
        source = os.environ if environ is None else environ
        environment = source.get("LXL_ENV", "development").strip().lower()
        if not environment:
            raise SecurityConfigurationError("LXL_ENV cannot be empty")

        configured_secret = source.get("JWT_SECRET_KEY", "")
        if configured_secret and len(configured_secret) < 32:
            raise SecurityConfigurationError("JWT_SECRET_KEY must contain at least 32 characters")
        if not configured_secret and environment in {"prod", "production"}:
            raise SecurityConfigurationError("JWT_SECRET_KEY is required when LXL_ENV=production")

        secret_is_ephemeral = not configured_secret
        jwt_secret = configured_secret or secrets.token_urlsafe(48)
        bind_host = source.get("LXL_BIND_HOST", "127.0.0.1").strip()
        if not bind_host:
            raise SecurityConfigurationError("LXL_BIND_HOST cannot be empty")

        is_production = environment in {"prod", "production"}
        return cls(
            environment=environment,
            jwt_secret=jwt_secret,
            jwt_secret_is_ephemeral=secret_is_ephemeral,
            bind_host=bind_host,
            access_token_expire_hours=_read_int(
                source,
                "JWT_ACCESS_TOKEN_HOURS",
                default=24,
                minimum=1,
                maximum=168,
            ),
            registration_enabled=_read_bool(
                source,
                "LXL_REGISTRATION_ENABLED",
                default=not is_production,
            ),
            auth_rate_limit_attempts=_read_int(
                source,
                "LXL_AUTH_RATE_LIMIT_ATTEMPTS",
                default=10,
                minimum=1,
                maximum=100,
            ),
            auth_rate_limit_window_seconds=_read_int(
                source,
                "LXL_AUTH_RATE_LIMIT_WINDOW_SECONDS",
                default=60,
                minimum=1,
                maximum=3600,
            ),
        )
