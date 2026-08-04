"""Deterministic A-share paper broker backed by the portfolio ledger."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.lxl_quantaxis.execution.orders import Fill, MarketQuote, Order, OrderSide, OrderStatus
from src.lxl_quantaxis.portfolio.accounting import FillSide, PortfolioLedger, TradeFill


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    orders_match_fills: bool
    fills_match_ledger: bool
    positions_non_negative: bool
    cash_balances: tuple[tuple[str, Decimal], ...]

    @property
    def balanced(self) -> bool:
        return self.orders_match_fills and self.fills_match_ledger and self.positions_non_negative


class PaperBroker:
    """Stateful simulator; inputs and persisted records remain immutable."""

    def __init__(self, *, initial_cash: Decimal, currency: str = "CNY") -> None:
        self.orders: dict[str, Order] = {}
        self.fills: list[Fill] = []
        self.ledger = PortfolioLedger(initial_cash, currency)

    def submit(self, order: Order) -> Order:
        existing = self.orders.get(order.order_id)
        if existing is not None:
            comparable = (existing.symbol, existing.side, existing.quantity, existing.limit_price)
            incoming = (order.symbol, order.side, order.quantity, order.limit_price)
            if comparable != incoming:
                raise ValueError("idempotency key was reused for a different order")
            return existing
        reason = self._submission_rejection(order)
        accepted = order.reject(reason) if reason else order.accept()
        self.orders[order.order_id] = accepted
        return accepted

    def execute(self, order_id: str, quote: MarketQuote, *, executed_at: datetime) -> Fill | None:
        order = self.orders[order_id]
        if order.status not in {OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}:
            return None
        if quote.symbol != order.symbol:
            raise ValueError("quote symbol does not match order")
        if (order.side is OrderSide.BUY and quote.limit_up) or (order.side is OrderSide.SELL and quote.limit_down):
            return None
        if order.limit_price is not None and (
            (order.side is OrderSide.BUY and quote.price > order.limit_price)
            or (order.side is OrderSide.SELL and quote.price < order.limit_price)
        ):
            return None
        quantity = min(order.remaining_quantity, max(quote.available_quantity, 0))
        if order.side is OrderSide.BUY:
            affordable = int(self.ledger.state().cash.get(self.ledger.base_currency, Decimal("0")) / quote.price)
            quantity = min(quantity, affordable)
        else:
            quantity = min(quantity, self._sellable_quantity(order.symbol, executed_at))
        if quantity <= 0:
            return None
        fill = Fill(
            fill_id=f"{order.order_id}:{len(self.fills) + 1}",
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=quantity,
            price=quote.price,
            executed_at=executed_at,
        )
        self.orders[order_id] = order.apply_fill(quantity)
        self.fills.append(fill)
        self.ledger = self.ledger.post_fill(
            TradeFill(
                fill.fill_id,
                fill.executed_at,
                fill.symbol,
                FillSide(fill.side.value),
                fill.quantity,
                fill.price,
            )
        )
        return fill

    def cancel(self, order_id: str) -> Order:
        cancelled = self.orders[order_id].cancel()
        self.orders[order_id] = cancelled
        return cancelled

    def reconcile(self) -> ReconciliationReport:
        fill_totals: dict[str, int] = {}
        for fill in self.fills:
            fill_totals[fill.order_id] = fill_totals.get(fill.order_id, 0) + fill.quantity
        orders_match = all(
            order.filled_quantity == fill_totals.get(order_id, 0) for order_id, order in self.orders.items()
        )
        ledger_ids = {entry.fill_id for entry in self.ledger.entries if isinstance(entry, TradeFill)}
        fills_match = ledger_ids == {fill.fill_id for fill in self.fills}
        state = self.ledger.state()
        return ReconciliationReport(
            orders_match,
            fills_match,
            all(position.quantity >= 0 for position in state.positions.values()),
            tuple(sorted(state.cash.items())),
        )

    def _submission_rejection(self, order: Order) -> str:
        if not order.order_id.strip() or not order.symbol.strip() or order.quantity <= 0:
            return "invalid order fields"
        if order.quantity % 100 != 0:
            return "A-share orders must use board lots of 100"
        return ""

    def _sellable_quantity(self, symbol: str, executed_at: datetime) -> int:
        eligible_buys = sum(
            fill.quantity
            for fill in self.fills
            if fill.symbol == symbol and fill.side is OrderSide.BUY and fill.executed_at.date() < executed_at.date()
        )
        prior_sells = sum(fill.quantity for fill in self.fills if fill.symbol == symbol and fill.side is OrderSide.SELL)
        return eligible_buys - prior_sells
