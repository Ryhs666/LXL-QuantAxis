"""Point-in-time data access for deterministic backtests."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class BarView:
    index: int
    event_time: datetime
    available_at: datetime
    row: Any
    history: Any


class DataPortal:
    """Expose only bars available at a given event-loop index."""

    REQUIRED_COLUMNS = frozenset({"date", "open", "high", "low", "close", "volume"})

    def __init__(self, data: Any) -> None:
        pandas = importlib.import_module("pandas")
        missing = self.REQUIRED_COLUMNS - set(data.columns)
        if missing:
            raise ValueError(f"backtest data missing column(s): {', '.join(sorted(missing))}")
        if len(data) == 0:
            raise ValueError("backtest data cannot be empty")
        self._data = data.sort_values("date", kind="stable").reset_index(drop=True).copy()
        timestamps = pandas.to_datetime(self._data["date"], errors="raise", utc=True)
        if timestamps.duplicated().any():
            raise ValueError("backtest bar dates must be unique")
        self._timestamps = timestamps

    def __len__(self) -> int:
        return len(self._data)

    @property
    def data(self) -> Any:
        return self._data.copy()

    def bar(self, index: int) -> BarView:
        if not 0 <= index < len(self):
            raise IndexError("bar index is outside the data portal")
        timestamp = self._timestamps.iloc[index].to_pydatetime()
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        return BarView(
            index=index,
            event_time=timestamp,
            available_at=timestamp,
            row=self._data.iloc[index].copy(),
            history=self._data.iloc[: index + 1].copy(),
        )

    def next_index(self, index: int) -> int | None:
        candidate = index + 1
        return candidate if candidate < len(self) else None
