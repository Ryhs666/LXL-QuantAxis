"""Warning-first quality gate and quarantine behavior."""

import unittest

from src.lxl_quantaxis.core import Instant
from src.lxl_quantaxis.data.providers import DataKind, PointInTimeRecord
from src.lxl_quantaxis.data.quality import (
    DataQualityError,
    InMemoryQuarantine,
    QualityGate,
    QualityMode,
    reconcile_numeric_field,
)


def _market_record(
    *,
    provider: str = "vendor-a",
    close: float = 10.0,
    high: float = 11.0,
    low: float = 9.0,
    adjustment_factor: float = 1.0,
) -> PointInTimeRecord:
    return PointInTimeRecord.create(
        kind=DataKind.MARKET,
        logical_key="CN:600519:2026-08-01",
        provider=provider,
        event_time=Instant.parse("2026-08-01T07:00:00Z"),
        available_at=Instant.parse("2026-08-01T07:01:00Z"),
        ingested_at=Instant.parse("2026-08-01T07:02:00Z"),
        revision_id=f"{provider}-1",
        payload={
            "open": 10.0,
            "high": high,
            "low": low,
            "close": close,
            "volume": 1000,
            "adjustment_factor": adjustment_factor,
        },
    )


class QualityGateTests(unittest.TestCase):
    def test_bad_data_is_quarantined_without_blocking_warning_mode(self) -> None:
        quarantine = InMemoryQuarantine()
        gate = QualityGate(mode=QualityMode.WARNING, quarantine=quarantine)
        invalid = _market_record(high=8.0, low=9.0, adjustment_factor=0.0)

        report = gate.evaluate((invalid,), as_of=Instant.parse("2026-08-02T00:00:00Z"))

        self.assertEqual(report.accepted, ())
        self.assertEqual(report.quarantined, (invalid,))
        self.assertEqual(len(quarantine.entries()), 1)
        self.assertIn("market.price_bounds", {issue.code for issue in report.issues})
        self.assertIn("market.adjustment_factor", {issue.code for issue in report.issues})

    def test_blocking_mode_raises_after_preserving_quarantine_evidence(self) -> None:
        quarantine = InMemoryQuarantine()
        gate = QualityGate(mode=QualityMode.BLOCKING, quarantine=quarantine)

        with self.assertRaises(DataQualityError):
            gate.evaluate((_market_record(high=8.0),), as_of=Instant.parse("2026-08-02T00:00:00Z"))

        self.assertEqual(len(quarantine.entries()), 1)

    def test_future_availability_is_detected_as_leakage(self) -> None:
        record = _market_record()
        report = QualityGate().evaluate((record,), as_of=Instant.parse("2026-08-01T07:00:30Z"))

        self.assertIn("pit.future_availability", {issue.code for issue in report.issues})
        self.assertEqual(report.accepted, ())

    def test_cross_source_sample_reconciliation_uses_tolerance(self) -> None:
        left = _market_record(provider="vendor-a", close=100.0)
        right = _market_record(provider="vendor-b", close=103.0)

        issues = reconcile_numeric_field((left, right), field="close", relative_tolerance=0.01)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "reconciliation.close")

    def test_market_gap_and_return_outlier_are_flagged_without_quarantine(self) -> None:
        first = _market_record(close=10.0)
        second = PointInTimeRecord.create(
            kind=DataKind.MARKET,
            logical_key="CN:600519:2026-08-20",
            provider="vendor-a",
            event_time=Instant.parse("2026-08-20T07:00:00Z"),
            available_at=Instant.parse("2026-08-20T07:01:00Z"),
            ingested_at=Instant.parse("2026-08-20T07:02:00Z"),
            revision_id="vendor-a-2",
            payload={"open": 19.0, "high": 21.0, "low": 18.0, "close": 20.0, "volume": 1000},
        )

        report = QualityGate().evaluate((first, second), as_of=Instant.parse("2026-08-21T00:00:00Z"))

        codes = {issue.code for issue in report.issues}
        self.assertIn("market.gap", codes)
        self.assertIn("market.return_outlier", codes)
        self.assertEqual(report.accepted, (first, second))


if __name__ == "__main__":
    unittest.main()
