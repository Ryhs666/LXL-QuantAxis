"""Timezone-safe temporal value objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True, slots=True, order=True)
class Instant:
    """An immutable UTC instant that rejects naive datetimes."""

    value: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.value, datetime):
            raise TypeError("instant value must be a datetime")
        if self.value.tzinfo is None or self.value.utcoffset() is None:
            raise ValueError("instant requires a timezone-aware datetime")
        object.__setattr__(self, "value", self.value.astimezone(UTC))

    @classmethod
    def parse(cls, value: str) -> Instant:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("instant must be a non-empty ISO 8601 string")
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"invalid ISO 8601 instant: {value!r}") from exc
        return cls(parsed)

    def isoformat(self) -> str:
        return self.value.isoformat().replace("+00:00", "Z")

    def add(self, delta: timedelta) -> Instant:
        if not isinstance(delta, timedelta):
            raise TypeError("instant delta must be timedelta")
        return Instant(self.value + delta)

    def to_dict(self) -> str:
        return self.isoformat()


@dataclass(frozen=True, slots=True)
class TimeRange:
    """Inclusive, ordered time interval."""

    start: Instant
    end: Instant

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("time range end cannot be earlier than start")

    def contains(self, instant: Instant) -> bool:
        return self.start <= instant <= self.end

    def to_dict(self) -> dict[str, str]:
        return {"start": self.start.isoformat(), "end": self.end.isoformat()}

    @classmethod
    def from_dict(cls, value: dict[str, str]) -> TimeRange:
        return cls(start=Instant.parse(value["start"]), end=Instant.parse(value["end"]))
