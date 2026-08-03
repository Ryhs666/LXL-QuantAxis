"""Deterministic next-bar execution models."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.lxl_quantaxis.backtest.engine import ScheduledSignal


@dataclass(frozen=True, slots=True)
class Fill:
    signal: Any
    signal_available_at: datetime
    executed_at: datetime
    price: float


class NextBarOpenFillModel:
    """Fill eligible signals at the next bar open with deterministic costs."""

    def __init__(
        self,
        *,
        slippage: float = 0.0,
        use_impact_cost: bool = False,
        impact_coefficient: float = 0.1,
        use_limit_order: bool = False,
        random_seed: int = 0,
    ) -> None:
        if slippage < 0 or impact_coefficient < 0:
            raise ValueError("fill costs cannot be negative")
        self.slippage = slippage
        self.use_impact_cost = use_impact_cost
        self.impact_coefficient = impact_coefficient
        self.use_limit_order = use_limit_order
        # Pseudorandomness is intentional: this is a seeded simulation, not a security boundary.
        self._random = random.Random(random_seed)  # nosec B311
        self.attempted = 0
        self.filled = 0
        self.cancelled = 0

    def fill(self, scheduled: ScheduledSignal, row: Any) -> Fill | None:
        signal = scheduled.signal
        action = str(signal.action).upper()
        base_price = float(row["open"])
        working_price = base_price
        if self.use_limit_order and action == "BUY":
            self.attempted += 1
            if self._random.randint(0, 100) >= 70:
                self.cancelled += 1
                return None
            spread = base_price * self._random.uniform(0.0001, 0.001)
            working_price -= spread
            self.filled += 1
        impact = self._impact(signal, row, base_price) if action in {"BUY", "SELL"} else 0.0
        direction = 1.0 if action in {"BUY", "COVER"} else -1.0
        price = working_price * (1.0 + direction * (self.slippage + impact))
        return Fill(signal, scheduled.available_at, scheduled.eligible_at, price)

    def _impact(self, signal: Any, row: Any, base_price: float) -> float:
        if not self.use_impact_cost:
            return 0.0
        volume = float(row.get("volume", 0.0))
        if volume <= 0:
            return 0.0
        order_ratio = (float(signal.price) * max(int(signal.quantity), 1)) / (base_price * volume)
        return self.impact_coefficient * order_ratio if order_ratio > 0.01 else 0.0

    @property
    def stats(self) -> dict[str, int]:
        return {"attempted": self.attempted, "filled": self.filled, "cancelled": self.cancelled}
