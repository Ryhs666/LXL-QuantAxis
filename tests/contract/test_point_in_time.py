"""Point-in-time provider and revision-history contracts."""

import unittest
from datetime import UTC, datetime

import pandas as pd

from src.backtest.providers import CallableDataProvider
from src.lxl_quantaxis.core import Instant
from src.lxl_quantaxis.data.providers import DataKind, PointInTimeRecord, RevisionHistory


def _instant(value: str) -> Instant:
    return Instant.parse(value)


class RevisionHistoryTests(unittest.TestCase):
    def test_historical_as_of_returns_latest_known_revision_without_overwrite(self) -> None:
        original = PointInTimeRecord.create(
            kind=DataKind.FINANCIAL,
            logical_key="CN:600519:revenue:2025Q4",
            provider="vendor-a",
            event_time=_instant("2025-12-31T00:00:00Z"),
            available_at=_instant("2026-01-31T08:00:00Z"),
            ingested_at=_instant("2026-01-31T08:05:00Z"),
            revision_id="vendor-a-r1",
            payload={"metric": "revenue", "value": 100, "currency": "CNY", "period_end": "2025-12-31"},
        )
        revised = PointInTimeRecord.create(
            kind=DataKind.FINANCIAL,
            logical_key=original.logical_key,
            provider="vendor-a",
            event_time=original.event_time,
            available_at=_instant("2026-02-15T08:00:00Z"),
            ingested_at=_instant("2026-02-15T08:02:00Z"),
            revision_id="vendor-a-r2",
            payload={"metric": "revenue", "value": 105, "currency": "CNY", "period_end": "2025-12-31"},
        )
        history = RevisionHistory().append(original).append(revised)

        january_view = history.as_of(_instant("2026-02-01T00:00:00Z"))
        february_view = history.as_of(_instant("2026-02-16T00:00:00Z"))

        self.assertEqual(january_view, (original,))
        self.assertEqual(february_view, (revised,))
        self.assertEqual(history.revisions(original.logical_key), (original, revised))

    def test_available_but_not_yet_ingested_record_is_not_known(self) -> None:
        record = PointInTimeRecord.create(
            kind=DataKind.NEWS,
            logical_key="news:example-1",
            provider="wire",
            event_time=_instant("2026-01-01T09:00:00Z"),
            available_at=_instant("2026-01-01T09:01:00Z"),
            ingested_at=_instant("2026-01-01T10:00:00Z"),
            revision_id="wire-1",
            payload={"title": "Example", "source_url": "https://example.com/1", "language": "en"},
        )
        history = RevisionHistory().append(record)

        self.assertEqual(history.as_of(_instant("2026-01-01T09:30:00Z")), ())
        self.assertEqual(history.as_of(_instant("2026-01-01T10:00:00Z")), (record,))


class LegacyProviderMappingTests(unittest.TestCase):
    def test_existing_provider_can_expose_inferred_pit_records(self) -> None:
        frame = pd.DataFrame([{"date": "2026-08-01", "open": 10, "high": 12, "low": 9, "close": 11, "volume": 1000}])
        provider = CallableDataProvider("fixture", "A股", lambda *args, **kwargs: frame.copy())
        as_of = Instant(datetime(2026, 8, 3, 8, tzinfo=UTC))

        records = provider.fetch_point_in_time("600519", "2026-08-01", as_of=as_of)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].kind, DataKind.MARKET)
        self.assertEqual(records[0].provider, "fixture")
        self.assertIn("legacy_availability_inferred", records[0].quality_flags)


if __name__ == "__main__":
    unittest.main()
