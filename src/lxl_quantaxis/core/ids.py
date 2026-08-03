"""Typed, immutable identifiers used to correlate V2 domain activity."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar, Self
from uuid import UUID, uuid4


class IdentifierError(ValueError):
    """Raised when a typed identifier is malformed."""


@dataclass(frozen=True, slots=True)
class Identifier:
    """Canonical prefixed UUID value object."""

    value: str
    prefix: ClassVar[str] = "id"

    def __post_init__(self) -> None:
        expected_prefix = f"{self.prefix}_"
        if not self.value.startswith(expected_prefix):
            raise IdentifierError(f"identifier must start with {expected_prefix!r}")
        payload = self.value[len(expected_prefix) :]
        if len(payload) != 32 or payload != payload.lower():
            raise IdentifierError("identifier payload must be 32 lowercase hexadecimal characters")
        try:
            parsed = UUID(hex=payload)
        except ValueError as exc:
            raise IdentifierError("identifier payload must be a UUID") from exc
        if parsed.hex != payload:
            raise IdentifierError("identifier payload is not canonical")

    @classmethod
    def new(cls, factory: Callable[[], UUID] = uuid4) -> Self:
        """Create an identifier, allowing a deterministic factory in tests."""

        return cls(f"{cls.prefix}_{factory().hex}")

    @classmethod
    def parse(cls, raw_value: str) -> Self:
        """Parse and validate a serialized identifier."""

        if not isinstance(raw_value, str):
            raise IdentifierError("identifier must be a string")
        return cls(raw_value.strip())

    def __str__(self) -> str:
        return self.value


class CorrelationId(Identifier):
    """Connect all events and operations belonging to one request or workflow."""

    prefix = "cor"


class EventId(Identifier):
    """Uniquely identify a domain event."""

    prefix = "evt"


class ResearchRunId(Identifier):
    """Uniquely identify a reproducible research run."""

    prefix = "run"


__all__ = ["CorrelationId", "EventId", "Identifier", "IdentifierError", "ResearchRunId"]
