"""N-bar signal delay queue for next-bar execution.

Signals generated at bar T are held until bar T+lag_periods
before being released for execution.  The last bar's signals
are always left unfilled (no future data).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _DelayedSignal:
    bar_index: int
    signal: Any
    release_at: int


@dataclass
class SignalLagQueue:
    """FIFO delay queue for point-in-time signal execution."""

    lag_periods: int = 1  # 0 = same-bar (no delay), 1 = next-bar (default)
    _pending: deque = field(default_factory=deque)

    def __post_init__(self) -> None:
        if self.lag_periods < 0:
            raise ValueError(f"lag_periods must be >= 0, got {self.lag_periods}")

    def push(self, bar_index: int, signal: Any, total_bars: int) -> None:
        """Enqueue a signal generated at bar_index."""
        if self.lag_periods == 0:
            return  # no delay — caller must handle immediately
        release = bar_index + self.lag_periods
        # Never release beyond the last bar (no future data)
        if release >= total_bars:
            return  # will never fill
        self._pending.append(_DelayedSignal(bar_index, signal, release))

    def pop_due(self, current_bar: int) -> list[Any]:
        """Return all signals whose release_at == current_bar."""
        due = []
        remaining = deque()
        while self._pending:
            item = self._pending.popleft()
            if item.release_at == current_bar:
                due.append(item.signal)
            else:
                remaining.append(item)
        self._pending = remaining
        return due

    def pop_unfilled(self) -> list[Any]:
        """Return all queued signals that will never fill (end of backtest)."""
        unfilled = [item.signal for item in self._pending]
        self._pending.clear()
        return unfilled

    def __len__(self) -> int:
        return len(self._pending)

    def is_empty(self) -> bool:
        return len(self._pending) == 0
