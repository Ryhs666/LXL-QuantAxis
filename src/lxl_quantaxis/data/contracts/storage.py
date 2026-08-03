"""Framework-independent storage contracts for the V2 data layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True, order=True)
class StorageKey:
    """A portable, root-relative storage key."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise TypeError("storage key must be a string")
        normalized = self.value.strip()
        if not normalized:
            raise ValueError("storage key cannot be empty")
        if "\\" in normalized or normalized.startswith("/"):
            raise ValueError("storage key must be a portable relative path")
        parts = normalized.split("/")
        if any(part in {"", ".", ".."} for part in parts) or ":" in parts[0]:
            raise ValueError("storage key cannot contain empty, absolute, or traversal segments")
        object.__setattr__(self, "value", "/".join(parts))

    @property
    def parts(self) -> tuple[str, ...]:
        return tuple(self.value.split("/"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class StorageMetadata:
    """Portable metadata returned by a storage implementation."""

    key: StorageKey
    size: int
    modified_at: datetime

    def __post_init__(self) -> None:
        if self.size < 0:
            raise ValueError("storage object size cannot be negative")
        if self.modified_at.tzinfo is None or self.modified_at.utcoffset() is None:
            raise ValueError("storage modification time must be timezone-aware")


@runtime_checkable
class StoragePort(Protocol):
    """Minimal binary object storage boundary used by domain-facing adapters."""

    def exists(self, key: StorageKey) -> bool: ...

    def read_bytes(self, key: StorageKey) -> bytes: ...

    def write_bytes(self, key: StorageKey, content: bytes) -> None: ...

    def metadata(self, key: StorageKey) -> StorageMetadata: ...

    def iter_keys(self, prefix: StorageKey | None = None) -> tuple[StorageKey, ...]: ...

    def delete(self, key: StorageKey) -> bool: ...
