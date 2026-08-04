"""Immutable order and fill state for paper execution."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(StrEnum):
    NEW = "new"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


TERMINAL_STATUSES = frozenset({OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED})


@dataclass(frozen=True, slots=True)
class Order:
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    submitted_at: datetime
    limit_price: Decimal | None = None
    status: OrderStatus = OrderStatus.NEW
    filled_quantity: int = 0
    rejection_reason: str = ""

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity

    def accept(self) -> Order:
        if self.status is not OrderStatus.NEW:
            raise ValueError("only new orders can be accepted")
        return replace(self, status=OrderStatus.ACCEPTED)

    def reject(self, reason: str) -> Order:
        if self.status is not OrderStatus.NEW or not reason.strip():
            raise ValueError("only new orders can be rejected with a reason")
        return replace(self, status=OrderStatus.REJECTED, rejection_reason=reason)

    def apply_fill(self, quantity: int) -> Order:
        if self.status not in {OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}:
            raise ValueError("order is not fillable")
        if quantity <= 0 or quantity > self.remaining_quantity:
            raise ValueError("fill quantity exceeds remaining order quantity")
        filled = self.filled_quantity + quantity
        status = OrderStatus.FILLED if filled == self.quantity else OrderStatus.PARTIALLY_FILLED
        return replace(self, filled_quantity=filled, status=status)

    def cancel(self) -> Order:
        if self.status not in {OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}:
            raise ValueError("order is not cancellable")
        return replace(self, status=OrderStatus.CANCELLED)


@dataclass(frozen=True, slots=True)
class Fill:
    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: Decimal
    executed_at: datetime


@dataclass(frozen=True, slots=True)
class MarketQuote:
    symbol: str
    price: Decimal
    available_quantity: int
    limit_up: bool = False
    limit_down: bool = False
