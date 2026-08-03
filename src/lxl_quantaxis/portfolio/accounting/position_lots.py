"""Immutable FIFO position lots."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PositionLot:
    fill_id: str
    quantity: int
    unit_cost: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not self.fill_id.strip() or self.quantity <= 0 or self.unit_cost <= 0:
            raise ValueError("position lot requires an id, positive quantity, and positive cost")


@dataclass(frozen=True, slots=True)
class Position:
    symbol: str
    lots: tuple[PositionLot, ...]

    @property
    def quantity(self) -> int:
        return sum(lot.quantity for lot in self.lots)

    @property
    def currency(self) -> str:
        if not self.lots:
            raise ValueError("empty position has no currency")
        return self.lots[0].currency

    @property
    def cost_basis(self) -> Decimal:
        return sum((lot.unit_cost * lot.quantity for lot in self.lots), start=Decimal("0"))

    @property
    def average_cost(self) -> Decimal:
        return self.cost_basis / self.quantity if self.quantity else Decimal("0")
