"""Dependency-free structured telemetry that cannot alter domain results."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Protocol, TypeVar

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="unscoped")
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class TelemetryEvent:
    name: str
    occurred_at: datetime
    correlation_id: str
    attributes: tuple[tuple[str, str], ...]


class TelemetrySink(Protocol):
    def emit(self, event: TelemetryEvent) -> None: ...


class InMemoryTelemetry:
    def __init__(self) -> None:
        self.events: list[TelemetryEvent] = []

    def emit(self, event: TelemetryEvent) -> None:
        self.events.append(event)


def correlation_scope(correlation_id: str) -> Token[str]:
    if not correlation_id.strip():
        raise ValueError("correlation id cannot be empty")
    return _correlation_id.set(correlation_id)


def reset_correlation(token: Token[str]) -> None:
    _correlation_id.reset(token)


def run_observed(
    name: str,
    operation: Callable[[], T],
    *,
    sink: TelemetrySink,
    attributes: Mapping[str, str] | None = None,
) -> T:
    """Run an operation and fail open if the telemetry sink is unavailable."""

    started = monotonic()
    try:
        result = operation()
    except Exception:
        _safe_emit(sink, name + ".failed", attributes, started)
        raise
    _safe_emit(sink, name + ".completed", attributes, started)
    return result


def _safe_emit(
    sink: TelemetrySink,
    name: str,
    attributes: Mapping[str, str] | None,
    started: float,
) -> None:
    values = dict(attributes or {})
    values["duration_ms"] = f"{(monotonic() - started) * 1000:.3f}"
    event = TelemetryEvent(
        name,
        datetime.now(UTC),
        _correlation_id.get(),
        tuple(sorted(values.items())),
    )
    try:
        sink.emit(event)
    except Exception:
        return
