"""Compatibility mapping from legacy OHLCV rows to PIT envelopes."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping

from src.lxl_quantaxis.core import Instant
from src.lxl_quantaxis.data.providers.contracts import DataKind, PointInTimeRecord


def map_legacy_market_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    provider: str,
    market: str,
    symbol: str,
    ingested_at: Instant,
) -> tuple[PointInTimeRecord, ...]:
    records: list[PointInTimeRecord] = []
    for row in rows:
        date_value = str(row["date"])[:10]
        event_time = Instant.parse(f"{date_value}T00:00:00Z")
        payload = {name: row[name] for name in ("open", "high", "low", "close", "volume")}
        digest_input = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()
        revision_id = f"legacy-{hashlib.sha256(digest_input).hexdigest()[:16]}"
        records.append(
            PointInTimeRecord.create(
                kind=DataKind.MARKET,
                logical_key=f"{market}:{symbol}:{date_value}",
                provider=provider,
                event_time=event_time,
                available_at=event_time,
                ingested_at=ingested_at,
                revision_id=revision_id,
                payload=payload,
                quality_flags=("legacy_availability_inferred", "legacy_revision_inferred"),
            )
        )
    return tuple(records)
