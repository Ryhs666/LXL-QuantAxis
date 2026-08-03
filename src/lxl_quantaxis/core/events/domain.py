"""Deeply immutable and canonically serializable domain events."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field

from src.lxl_quantaxis.core.contracts import Instant
from src.lxl_quantaxis.core.ids import CorrelationId, EventId, ResearchRunId


def _freeze_json(value: object, path: str = "payload") -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite float")
        return value
    if isinstance(value, Mapping):
        items: list[tuple[str, object]] = []
        for key, child in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} object keys must be strings")
            items.append((key, _freeze_json(child, f"{path}.{key}")))
        return FrozenJsonObject(tuple(sorted(items)))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_freeze_json(child, f"{path}[]") for child in value)
    raise TypeError(f"{path} contains unsupported value type {type(value).__name__}")


def _thaw_json(value: object) -> object:
    if isinstance(value, FrozenJsonObject):
        return {key: _thaw_json(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(child) for child in value]
    return value


@dataclass(frozen=True, slots=True)
class FrozenJsonObject(Mapping[str, object]):
    """Hashable, recursively immutable JSON object."""

    _items: tuple[tuple[str, object], ...] = ()

    def __getitem__(self, key: str) -> object:
        for item_key, value in self._items:
            if item_key == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (key for key, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def to_dict(self) -> dict[str, object]:
        return {key: _thaw_json(value) for key, value in self._items}


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Immutable event envelope with correlation and causation metadata."""

    event_id: EventId
    event_type: str
    occurred_at: Instant
    correlation_id: CorrelationId
    payload: FrozenJsonObject = field(default_factory=FrozenJsonObject)
    causation_id: EventId | None = None
    aggregate_id: ResearchRunId | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        if re.fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)+", self.event_type) is None:
            raise ValueError("event_type must be a lowercase dotted domain name")
        if isinstance(self.schema_version, bool) or self.schema_version < 1:
            raise ValueError("schema_version must be a positive integer")
        if not isinstance(self.payload, FrozenJsonObject):
            frozen = _freeze_json(self.payload)
            if not isinstance(frozen, FrozenJsonObject):
                raise TypeError("event payload must be an object")
            object.__setattr__(self, "payload", frozen)

    @classmethod
    def create(
        cls,
        *,
        event_type: str,
        occurred_at: Instant,
        payload: Mapping[str, object] | None = None,
        event_id: EventId | None = None,
        correlation_id: CorrelationId | None = None,
        causation_id: EventId | None = None,
        aggregate_id: ResearchRunId | None = None,
        schema_version: int = 1,
    ) -> DomainEvent:
        frozen_payload = _freeze_json({} if payload is None else payload)
        if not isinstance(frozen_payload, FrozenJsonObject):
            raise TypeError("event payload must be an object")
        return cls(
            event_id=event_id or EventId.new(),
            event_type=event_type,
            occurred_at=occurred_at,
            correlation_id=correlation_id or CorrelationId.new(),
            payload=frozen_payload,
            causation_id=causation_id,
            aggregate_id=aggregate_id,
            schema_version=schema_version,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "correlation_id": str(self.correlation_id),
            "causation_id": None if self.causation_id is None else str(self.causation_id),
            "aggregate_id": None if self.aggregate_id is None else str(self.aggregate_id),
            "schema_version": self.schema_version,
            "payload": self.payload.to_dict(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> DomainEvent:
        payload = value.get("payload", {})
        if not isinstance(payload, Mapping):
            raise TypeError("event payload must be an object")
        causation_value = value.get("causation_id")
        aggregate_value = value.get("aggregate_id")
        return cls.create(
            event_id=EventId.parse(str(value["event_id"])),
            event_type=str(value["event_type"]),
            occurred_at=Instant.parse(str(value["occurred_at"])),
            correlation_id=CorrelationId.parse(str(value["correlation_id"])),
            causation_id=None if causation_value is None else EventId.parse(str(causation_value)),
            aggregate_id=None if aggregate_value is None else ResearchRunId.parse(str(aggregate_value)),
            schema_version=int(str(value.get("schema_version", 1))),
            payload=payload,
        )

    @classmethod
    def from_json(cls, value: str) -> DomainEvent:
        payload = json.loads(value)
        if not isinstance(payload, dict):
            raise TypeError("domain event JSON must contain an object")
        return cls.from_dict(payload)
