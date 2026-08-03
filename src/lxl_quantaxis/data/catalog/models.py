"""Immutable dataset catalog records."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import cast

from src.lxl_quantaxis.core import Instant
from src.lxl_quantaxis.data.contracts import StorageKey

_DATASET_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SCHEMA_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class Dataset:
    """Stable identity and storage description for a logical dataset."""

    dataset_id: str
    name: str
    storage_key: StorageKey
    media_type: str
    schema_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.dataset_id, str) or not _DATASET_ID.fullmatch(self.dataset_id):
            raise ValueError("dataset_id must be a lowercase kebab-case identifier")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("dataset name cannot be empty")
        if not isinstance(self.media_type, str) or "/" not in self.media_type:
            raise ValueError("dataset media_type must be an IANA-style media type")
        if not isinstance(self.schema_version, str) or not _SCHEMA_VERSION.fullmatch(self.schema_version):
            raise ValueError("dataset schema_version must use major.minor.patch")

    def to_dict(self) -> dict[str, str]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "storage_key": str(self.storage_key),
            "media_type": self.media_type,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, value: dict[str, str]) -> Dataset:
        return cls(
            dataset_id=value["dataset_id"],
            name=value["name"],
            storage_key=StorageKey(value["storage_key"]),
            media_type=value["media_type"],
            schema_version=value["schema_version"],
        )


@dataclass(frozen=True, slots=True)
class DatasetSnapshot:
    """Content-addressed, immutable observation of a dataset."""

    dataset: Dataset
    content_hash: str
    byte_size: int
    captured_at: Instant
    row_count: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content_hash, str) or not _SHA256.fullmatch(self.content_hash):
            raise ValueError("content_hash must be a lowercase SHA-256 digest")
        if self.byte_size < 0:
            raise ValueError("snapshot byte_size cannot be negative")
        if self.row_count is not None and self.row_count < 0:
            raise ValueError("snapshot row_count cannot be negative")

    @property
    def snapshot_id(self) -> str:
        return f"{self.dataset.dataset_id}:{self.content_hash}"

    @classmethod
    def from_bytes(
        cls,
        *,
        dataset: Dataset,
        content: bytes,
        captured_at: Instant,
        row_count: int | None = None,
    ) -> DatasetSnapshot:
        if not isinstance(content, bytes):
            raise TypeError("snapshot content must be bytes")
        return cls(
            dataset=dataset,
            content_hash=hashlib.sha256(content).hexdigest(),
            byte_size=len(content),
            captured_at=captured_at,
            row_count=row_count,
        )

    def verify(self, content: bytes) -> bool:
        return len(content) == self.byte_size and hashlib.sha256(content).hexdigest() == self.content_hash

    def to_dict(self) -> dict[str, object]:
        return {
            "dataset": self.dataset.to_dict(),
            "content_hash": self.content_hash,
            "byte_size": self.byte_size,
            "captured_at": self.captured_at.isoformat(),
            "row_count": self.row_count,
        }

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> DatasetSnapshot:
        dataset_value = value["dataset"]
        if not isinstance(dataset_value, dict) or not all(
            isinstance(key, str) and isinstance(item, str) for key, item in dataset_value.items()
        ):
            raise ValueError("snapshot dataset must be an object")
        byte_size = value["byte_size"]
        if not isinstance(byte_size, int) or isinstance(byte_size, bool):
            raise ValueError("snapshot byte_size must be an integer")
        row_count = value.get("row_count")
        if row_count is not None and (not isinstance(row_count, int) or isinstance(row_count, bool)):
            raise ValueError("snapshot row_count must be an integer or null")
        return cls(
            dataset=Dataset.from_dict(cast(dict[str, str], dataset_value)),
            content_hash=str(value["content_hash"]),
            byte_size=byte_size,
            captured_at=Instant.parse(str(value["captured_at"])),
            row_count=row_count,
        )
