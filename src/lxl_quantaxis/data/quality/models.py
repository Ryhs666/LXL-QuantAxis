"""Data-quality findings, reports, and quarantine evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from src.lxl_quantaxis.data.providers import PointInTimeRecord


class QualityMode(StrEnum):
    WARNING = "warning"
    BLOCKING = "blocking"


class IssueSeverity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class QualityIssue:
    code: str
    message: str
    severity: IssueSeverity
    logical_key: str
    provider: str


@dataclass(frozen=True, slots=True)
class QualityReport:
    accepted: tuple[PointInTimeRecord, ...]
    quarantined: tuple[PointInTimeRecord, ...]
    issues: tuple[QualityIssue, ...]
    mode: QualityMode

    @property
    def clean(self) -> bool:
        return not self.issues


@dataclass(frozen=True, slots=True)
class QuarantineEntry:
    record: PointInTimeRecord
    issues: tuple[QualityIssue, ...]


class InMemoryQuarantine:
    """Append-only test and local adapter; persistent ports can replace it later."""

    def __init__(self) -> None:
        self._entries: list[QuarantineEntry] = []

    def add(self, record: PointInTimeRecord, issues: tuple[QualityIssue, ...]) -> None:
        self._entries.append(QuarantineEntry(record=record, issues=issues))

    def entries(self) -> tuple[QuarantineEntry, ...]:
        return tuple(self._entries)


class DataQualityError(RuntimeError):
    def __init__(self, report: QualityReport) -> None:
        self.report = report
        super().__init__(f"data quality gate blocked {len(report.quarantined)} record(s)")
