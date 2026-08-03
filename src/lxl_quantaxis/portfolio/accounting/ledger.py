"""Append-only portfolio ledger with FIFO lots and multi-currency valuation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import TypeAlias

from src.lxl_quantaxis.portfolio.accounting.position_lots import Position, PositionLot


class FillSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True, slots=True)
class TradeFill:
    fill_id: str
    executed_at: datetime
    symbol: str
    side: FillSide
    quantity: int
    price: Decimal
    fee: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    currency: str = "CNY"

    def __post_init__(self) -> None:
        if not isinstance(self.side, FillSide):
            object.__setattr__(self, "side", FillSide(self.side))
        if not self.fill_id.strip() or not self.symbol.strip() or self.quantity <= 0 or self.price <= 0:
            raise ValueError("fill requires ids, positive quantity, and positive price")
        if self.fee < 0 or self.tax < 0 or len(self.currency) != 3:
            raise ValueError("fill costs must be non-negative and currency must be ISO-4217")


@dataclass(frozen=True, slots=True)
class CashDividend:
    event_id: str
    effective_at: datetime
    symbol: str
    amount: Decimal
    currency: str = "CNY"

    def __post_init__(self) -> None:
        if not self.event_id.strip() or not self.symbol.strip() or self.amount < 0 or len(self.currency) != 3:
            raise ValueError("dividend fields are invalid")


LedgerEntry: TypeAlias = TradeFill | CashDividend


@dataclass(frozen=True, slots=True)
class LedgerState:
    cash: Mapping[str, Decimal]
    positions: Mapping[str, Position]
    realized_pnl: Mapping[str, Decimal]
    fees: Mapping[str, Decimal]
    taxes: Mapping[str, Decimal]
    dividends: Mapping[str, Decimal]


@dataclass(frozen=True, slots=True)
class PortfolioValuation:
    cash: Decimal
    positions: Decimal
    total: Decimal
    base_currency: str


@dataclass(frozen=True, slots=True)
class PortfolioLedger:
    initial_cash: Decimal
    base_currency: str = "CNY"
    entries: tuple[LedgerEntry, ...] = ()

    def __post_init__(self) -> None:
        if self.initial_cash < 0 or len(self.base_currency) != 3:
            raise ValueError("ledger cash and base currency are invalid")
        ids = [entry.fill_id if isinstance(entry, TradeFill) else entry.event_id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("ledger entry ids must be unique")

    def post_fill(self, fill: TradeFill) -> PortfolioLedger:
        if any(isinstance(entry, TradeFill) and entry.fill_id == fill.fill_id for entry in self.entries):
            raise ValueError(f"duplicate fill id: {fill.fill_id}")
        current = self.state()
        position = current.positions.get(fill.symbol)
        if fill.side is FillSide.SELL and (position is None or position.quantity < fill.quantity):
            raise ValueError("sell quantity exceeds the current position")
        if position is not None and position.currency != fill.currency:
            raise ValueError("a position cannot mix settlement currencies")
        return PortfolioLedger(self.initial_cash, self.base_currency, (*self.entries, fill))

    def post_dividend(self, dividend: CashDividend) -> PortfolioLedger:
        if any(isinstance(entry, CashDividend) and entry.event_id == dividend.event_id for entry in self.entries):
            raise ValueError(f"duplicate dividend id: {dividend.event_id}")
        return PortfolioLedger(self.initial_cash, self.base_currency, (*self.entries, dividend))

    def state(self) -> LedgerState:
        cash: dict[str, Decimal] = {self.base_currency: self.initial_cash}
        lots: dict[str, list[PositionLot]] = {}
        realized: dict[str, Decimal] = {}
        fees: dict[str, Decimal] = {}
        taxes: dict[str, Decimal] = {}
        dividends: dict[str, Decimal] = {}
        for entry in self.entries:
            if isinstance(entry, CashDividend):
                cash[entry.currency] = cash.get(entry.currency, Decimal("0")) + entry.amount
                dividends[entry.currency] = dividends.get(entry.currency, Decimal("0")) + entry.amount
                continue
            gross = entry.price * entry.quantity
            fees[entry.currency] = fees.get(entry.currency, Decimal("0")) + entry.fee
            taxes[entry.currency] = taxes.get(entry.currency, Decimal("0")) + entry.tax
            cash.setdefault(entry.currency, Decimal("0"))
            if entry.side is FillSide.BUY:
                cash[entry.currency] -= gross + entry.fee + entry.tax
                lots.setdefault(entry.symbol, []).append(
                    PositionLot(entry.fill_id, entry.quantity, entry.price, entry.currency)
                )
            else:
                cash[entry.currency] += gross - entry.fee - entry.tax
                cost, remaining = _consume_fifo(lots.get(entry.symbol, []), entry.quantity)
                realized[entry.currency] = (
                    realized.get(entry.currency, Decimal("0")) + gross - cost - entry.fee - entry.tax
                )
                lots[entry.symbol] = remaining
        positions = {
            symbol: Position(symbol, tuple(symbol_lots)) for symbol, symbol_lots in lots.items() if symbol_lots
        }
        return LedgerState(
            MappingProxyType(cash),
            MappingProxyType(positions),
            MappingProxyType(realized),
            MappingProxyType(fees),
            MappingProxyType(taxes),
            MappingProxyType(dividends),
        )

    def value(self, prices: Mapping[str, Decimal], fx_rates: Mapping[str, Decimal] | None = None) -> PortfolioValuation:
        state = self.state()
        rates = {self.base_currency: Decimal("1"), **dict(fx_rates or {})}
        missing_currencies = (set(state.cash) | {position.currency for position in state.positions.values()}) - set(
            rates
        )
        if missing_currencies:
            raise ValueError(f"missing FX rate(s): {', '.join(sorted(missing_currencies))}")
        missing_prices = set(state.positions) - set(prices)
        if missing_prices:
            raise ValueError(f"missing market price(s): {', '.join(sorted(missing_prices))}")
        cash_value = sum((amount * rates[currency] for currency, amount in state.cash.items()), Decimal("0"))
        position_value = sum(
            (
                Decimal(position.quantity) * prices[symbol] * rates[position.currency]
                for symbol, position in state.positions.items()
            ),
            Decimal("0"),
        )
        return PortfolioValuation(cash_value, position_value, cash_value + position_value, self.base_currency)


def _consume_fifo(lots: list[PositionLot], quantity: int) -> tuple[Decimal, list[PositionLot]]:
    remaining_quantity = quantity
    cost = Decimal("0")
    remaining_lots: list[PositionLot] = []
    for index, lot in enumerate(lots):
        consumed = min(lot.quantity, remaining_quantity)
        cost += lot.unit_cost * consumed
        leftover = lot.quantity - consumed
        if leftover:
            remaining_lots.append(PositionLot(lot.fill_id, leftover, lot.unit_cost, lot.currency))
        remaining_quantity -= consumed
        if remaining_quantity == 0:
            remaining_lots.extend(lots[index + 1 :])
            break
    if remaining_quantity:
        raise ValueError("insufficient FIFO lots")
    return cost, remaining_lots
