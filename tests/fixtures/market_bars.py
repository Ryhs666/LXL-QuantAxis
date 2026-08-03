"""Deterministic OHLCV fixtures with no network or filesystem access."""

from __future__ import annotations

import pandas as pd


def daily_bars(
    closes: tuple[float, ...] = (10.0, 11.0, 12.0),
    *,
    symbol: str = "600000",
    start: str = "2024-01-02",
) -> pd.DataFrame:
    """Build a minimal, internally consistent daily OHLCV frame."""
    dates = pd.bdate_range(start=start, periods=len(closes))
    rows = []
    for date, close in zip(dates, closes):
        rows.append(
            {
                "date": date,
                "symbol": symbol,
                "open": close - 0.2,
                "high": close + 0.3,
                "low": close - 0.4,
                "close": close,
                "volume": 1_000_000,
            }
        )
    return pd.DataFrame(rows)
