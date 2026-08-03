"""Append-only revision history and deterministic as-of selection."""

from __future__ import annotations

from dataclasses import dataclass

from src.lxl_quantaxis.core import Instant
from src.lxl_quantaxis.data.providers.contracts import PointInTimeRecord


@dataclass(frozen=True, slots=True)
class RevisionHistory:
    records: tuple[PointInTimeRecord, ...] = ()

    def append(self, record: PointInTimeRecord) -> RevisionHistory:
        identity = (record.provider, record.logical_key, record.revision_id)
        if any((item.provider, item.logical_key, item.revision_id) == identity for item in self.records):
            raise ValueError(f"duplicate provider revision: {identity!r}")
        ordered = tuple(
            sorted(
                (*self.records, record),
                key=lambda item: (item.logical_key, item.available_at, item.ingested_at, item.revision_id),
            )
        )
        return RevisionHistory(ordered)

    def revisions(self, logical_key: str) -> tuple[PointInTimeRecord, ...]:
        return tuple(item for item in self.records if item.logical_key == logical_key)

    def as_of(self, as_of: Instant, *, known_at: Instant | None = None) -> tuple[PointInTimeRecord, ...]:
        knowledge_time = as_of if known_at is None else known_at
        selected: dict[str, PointInTimeRecord] = {}
        for record in self.records:
            if record.available_at > as_of or record.ingested_at > knowledge_time:
                continue
            current = selected.get(record.logical_key)
            if current is None or (
                record.available_at,
                record.ingested_at,
                record.revision_id,
            ) > (
                current.available_at,
                current.ingested_at,
                current.revision_id,
            ):
                selected[record.logical_key] = record
        return tuple(selected[key] for key in sorted(selected))
