"""Explicit signal-availability and execution scheduling."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.lxl_quantaxis.backtest.data_portal import BarView, DataPortal


@dataclass(frozen=True, slots=True)
class ScheduledSignal:
    signal: Any
    signal_index: int
    available_at: datetime
    eligible_index: int
    eligible_at: datetime


class BacktestEventLoop:
    """Schedule close-derived signals for the next available bar."""

    def __init__(self, portal: DataPortal) -> None:
        self.portal = portal
        self._scheduled: dict[int, list[ScheduledSignal]] = {}

    def bars(self) -> Iterator[BarView]:
        for index in range(len(self.portal)):
            yield self.portal.bar(index)

    def schedule(self, signal: Any, signal_index: int) -> ScheduledSignal | None:
        eligible_index = self.portal.next_index(signal_index)
        if eligible_index is None:
            return None
        current = self.portal.bar(signal_index)
        eligible = self.portal.bar(eligible_index)
        scheduled = ScheduledSignal(
            signal=signal,
            signal_index=signal_index,
            available_at=current.available_at,
            eligible_index=eligible_index,
            eligible_at=eligible.event_time,
        )
        self._scheduled.setdefault(eligible_index, []).append(scheduled)
        return scheduled

    def due(self, index: int) -> tuple[ScheduledSignal, ...]:
        return tuple(self._scheduled.pop(index, ()))
