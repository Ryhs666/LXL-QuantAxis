"""Immutable Alpha Memory domain records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ConfirmationStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ResearchNote:
    note_id: str
    organization_id: str
    body: str
    created_at: datetime
    source: str = "manual"


@dataclass(frozen=True, slots=True)
class Thesis:
    thesis_id: str
    organization_id: str
    note_id: str
    statement: str
    assumptions: tuple[str, ...]
    risks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MemoryStrategy:
    strategy_id: str
    organization_id: str
    name: str
    created_at: datetime
    legacy_key: str | None = None


@dataclass(frozen=True, slots=True)
class StrategyVersion:
    strategy_id: str
    organization_id: str
    version: int
    specification_json: str
    created_at: datetime
    status: ConfirmationStatus = ConfirmationStatus.DRAFT


@dataclass(frozen=True, slots=True)
class DatasetSnapshot:
    snapshot_id: str
    organization_id: str
    content_hash: str
    data_as_of: datetime


@dataclass(frozen=True, slots=True)
class ResearchRun:
    run_id: str
    organization_id: str
    strategy_id: str
    strategy_version: int
    snapshot_id: str
    result_json: str
    started_at: datetime


@dataclass(frozen=True, slots=True)
class MemoryLink:
    link_id: str
    organization_id: str
    source_type: str
    source_id: str
    target_type: str
    target_id: str
