"""Point-in-time envelopes shared by all data providers."""

from __future__ import annotations

import math
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from src.lxl_quantaxis.core import Instant


class DataKind(StrEnum):
    MARKET = "market"
    FINANCIAL = "financial"
    NEWS = "news"


@dataclass(frozen=True, slots=True)
class FrozenPayload(Mapping[str, object]):
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
        return {key: _thaw(value) for key, value in self._items}


def _freeze(value: object, path: str = "payload") -> object:
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
                raise TypeError(f"{path} keys must be strings")
            items.append((key, _freeze(child, f"{path}.{key}")))
        return FrozenPayload(tuple(sorted(items)))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_freeze(child, f"{path}[]") for child in value)
    raise TypeError(f"{path} contains unsupported type {type(value).__name__}")


def _thaw(value: object) -> object:
    if isinstance(value, FrozenPayload):
        return value.to_dict()
    if isinstance(value, tuple):
        return [_thaw(child) for child in value]
    return value


@dataclass(frozen=True, slots=True)
class PointInTimeRecord:
    """Immutable provider revision with explicit availability semantics."""

    kind: DataKind
    logical_key: str
    provider: str
    event_time: Instant
    available_at: Instant
    ingested_at: Instant
    revision_id: str
    payload: FrozenPayload = field(default_factory=FrozenPayload)
    quality_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.kind, DataKind):
            object.__setattr__(self, "kind", DataKind(self.kind))
        if not isinstance(self.logical_key, str) or not self.logical_key.strip():
            raise ValueError("logical_key cannot be empty")
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError("provider cannot be empty")
        if (
            not isinstance(self.revision_id, str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", self.revision_id) is None
        ):
            raise ValueError("revision_id contains unsupported characters")
        if not isinstance(self.payload, FrozenPayload):
            frozen = _freeze(self.payload)
            if not isinstance(frozen, FrozenPayload):
                raise TypeError("record payload must be an object")
            object.__setattr__(self, "payload", frozen)
        normalized_flags = tuple(sorted(set(self.quality_flags)))
        if any(not isinstance(flag, str) or not flag for flag in normalized_flags):
            raise ValueError("quality flags must be non-empty strings")
        object.__setattr__(self, "quality_flags", normalized_flags)

    @classmethod
    def create(
        cls,
        *,
        kind: DataKind,
        logical_key: str,
        provider: str,
        event_time: Instant,
        available_at: Instant,
        ingested_at: Instant,
        revision_id: str,
        payload: Mapping[str, object],
        quality_flags: Sequence[str] = (),
    ) -> PointInTimeRecord:
        frozen = _freeze(payload)
        if not isinstance(frozen, FrozenPayload):
            raise TypeError("record payload must be an object")
        return cls(
            kind=kind,
            logical_key=logical_key.strip(),
            provider=provider.strip(),
            event_time=event_time,
            available_at=available_at,
            ingested_at=ingested_at,
            revision_id=revision_id,
            payload=frozen,
            quality_flags=tuple(quality_flags),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "logical_key": self.logical_key,
            "provider": self.provider,
            "event_time": self.event_time.isoformat(),
            "available_at": self.available_at.isoformat(),
            "ingested_at": self.ingested_at.isoformat(),
            "revision_id": self.revision_id,
            "payload": self.payload.to_dict(),
            "quality_flags": list(self.quality_flags),
        }


class PointInTimeProvider(Protocol):
    @property
    def name(self) -> str: ...

    def fetch_as_of(self, *, as_of: Instant) -> tuple[PointInTimeRecord, ...]: ...
