"""Warning-first schema, PIT, gap, outlier, and adjustment checks."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import timedelta

from src.lxl_quantaxis.core import Instant
from src.lxl_quantaxis.data.providers import DataKind, PointInTimeRecord, SchemaViolation
from src.lxl_quantaxis.data.providers.financial import validate_financial_record
from src.lxl_quantaxis.data.providers.market import validate_market_record
from src.lxl_quantaxis.data.providers.news import validate_news_record
from src.lxl_quantaxis.data.quality.models import (
    DataQualityError,
    InMemoryQuarantine,
    IssueSeverity,
    QualityIssue,
    QualityMode,
    QualityReport,
)

SchemaValidator = Callable[[PointInTimeRecord], tuple[SchemaViolation, ...]]

_VALIDATORS: dict[DataKind, SchemaValidator] = {
    DataKind.MARKET: validate_market_record,
    DataKind.FINANCIAL: validate_financial_record,
    DataKind.NEWS: validate_news_record,
}


class QualityGate:
    """Evaluate records and preserve invalid versions before optional blocking."""

    def __init__(
        self,
        *,
        mode: QualityMode = QualityMode.WARNING,
        quarantine: InMemoryQuarantine | None = None,
        maximum_market_gap: timedelta = timedelta(days=7),
        outlier_return: float = 0.5,
    ) -> None:
        self.mode = QualityMode(mode)
        self.quarantine = quarantine or InMemoryQuarantine()
        self.maximum_market_gap = maximum_market_gap
        self.outlier_return = outlier_return

    @staticmethod
    def _issue(record: PointInTimeRecord, code: str, message: str, severity: IssueSeverity) -> QualityIssue:
        return QualityIssue(
            code=code,
            message=message,
            severity=severity,
            logical_key=record.logical_key,
            provider=record.provider,
        )

    def _record_issues(self, record: PointInTimeRecord, as_of: Instant) -> tuple[QualityIssue, ...]:
        issues: list[QualityIssue] = []
        if record.event_time > record.available_at:
            issues.append(
                self._issue(
                    record, "pit.event_after_availability", "event_time exceeds available_at", IssueSeverity.ERROR
                )
            )
        if record.available_at > record.ingested_at:
            issues.append(
                self._issue(
                    record, "pit.availability_after_ingestion", "available_at exceeds ingested_at", IssueSeverity.ERROR
                )
            )
        if record.available_at > as_of:
            issues.append(
                self._issue(record, "pit.future_availability", "record was not available at as_of", IssueSeverity.ERROR)
            )
        if record.ingested_at > as_of:
            issues.append(
                self._issue(
                    record, "pit.future_ingestion", "record was not known to the system at as_of", IssueSeverity.ERROR
                )
            )
        for violation in _VALIDATORS[record.kind](record):
            issues.append(self._issue(record, violation.code, violation.message, IssueSeverity.ERROR))
        return tuple(issues)

    def _series_issues(self, records: Sequence[PointInTimeRecord]) -> tuple[QualityIssue, ...]:
        issues: list[QualityIssue] = []
        market_records = sorted(
            (record for record in records if record.kind is DataKind.MARKET),
            key=lambda record: (record.provider, record.logical_key.rsplit(":", 1)[0], record.event_time),
        )
        previous: PointInTimeRecord | None = None
        for record in market_records:
            series_key = (record.provider, record.logical_key.rsplit(":", 1)[0])
            previous_key = None if previous is None else (previous.provider, previous.logical_key.rsplit(":", 1)[0])
            if previous is not None and series_key == previous_key:
                if record.event_time.value - previous.event_time.value > self.maximum_market_gap:
                    issues.append(
                        self._issue(
                            record, "market.gap", "market series contains an unexpected gap", IssueSeverity.WARNING
                        )
                    )
                prior_close = previous.payload.get("close")
                close = record.payload.get("close")
                if (
                    isinstance(prior_close, (int, float))
                    and not isinstance(prior_close, bool)
                    and prior_close != 0
                    and isinstance(close, (int, float))
                    and not isinstance(close, bool)
                ):
                    change = abs(float(close) / float(prior_close) - 1.0)
                    if change > self.outlier_return:
                        issues.append(
                            self._issue(
                                record,
                                "market.return_outlier",
                                "market return exceeds configured threshold",
                                IssueSeverity.WARNING,
                            )
                        )
            previous = record
        return tuple(issues)

    def evaluate(self, records: Sequence[PointInTimeRecord], *, as_of: Instant) -> QualityReport:
        accepted: list[PointInTimeRecord] = []
        quarantined: list[PointInTimeRecord] = []
        issues: list[QualityIssue] = []
        for record in records:
            record_issues = self._record_issues(record, as_of)
            issues.extend(record_issues)
            if any(issue.severity is IssueSeverity.ERROR for issue in record_issues):
                quarantined.append(record)
                self.quarantine.add(record, record_issues)
            else:
                accepted.append(record)
        issues.extend(self._series_issues(accepted))
        report = QualityReport(
            accepted=tuple(accepted),
            quarantined=tuple(quarantined),
            issues=tuple(issues),
            mode=self.mode,
        )
        if self.mode is QualityMode.BLOCKING and quarantined:
            raise DataQualityError(report)
        return report
