"""Explicit clocks for point-in-time-safe research workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.lxl_quantaxis.core.contracts import Instant


class FutureDataError(ValueError):
    """Raised when research attempts to consume data not yet available."""


class ClockSource(Protocol):
    """Minimal injectable time source."""

    def now(self) -> Instant:
        """Return the current instant."""


@dataclass(frozen=True, slots=True)
class SystemClock:
    """Production clock backed by the system UTC clock."""

    def now(self) -> Instant:
        return Instant(datetime.now(UTC))


@dataclass(slots=True)
class FrozenClock:
    """Controllable clock for deterministic research and tests."""

    current: Instant

    def now(self) -> Instant:
        return self.current

    def advance(self, delta: timedelta) -> None:
        if not isinstance(delta, timedelta):
            raise TypeError("clock delta must be timedelta")
        self.current = self.current.add(delta)


@dataclass(frozen=True, slots=True)
class ResearchClock:
    """Research time boundary with explicit timezone and PIT enforcement."""

    source: ClockSource = field(default_factory=SystemClock)
    timezone_name: str = "Asia/Shanghai"
    _timezone: ZoneInfo = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        try:
            timezone = ZoneInfo(self.timezone_name)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown IANA timezone: {self.timezone_name!r}") from exc
        object.__setattr__(self, "_timezone", timezone)

    @classmethod
    def at(cls, value: Instant | str, timezone_name: str = "Asia/Shanghai") -> ResearchClock:
        instant = Instant.parse(value) if isinstance(value, str) else value
        return cls(source=FrozenClock(instant), timezone_name=timezone_name)

    def now(self) -> Instant:
        return self.source.now()

    def local_now(self) -> datetime:
        return self.now().value.astimezone(self._timezone)

    def require_available(self, available_at: Instant) -> None:
        if available_at > self.now():
            raise FutureDataError(
                f"data available at {available_at.isoformat()} exceeds research time {self.now().isoformat()}"
            )
