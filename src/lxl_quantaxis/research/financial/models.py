"""Financial-analysis domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.lxl_quantaxis.core.contracts.money import Money


@dataclass(frozen=True, slots=True)
class FinancialPeriod:
    period_end: date
    available_on: date
    revenue: Money
    net_income: Money
    operating_cash_flow: Money
    equity: Money
    diluted_shares: Decimal

    def __post_init__(self) -> None:
        currencies = {
            self.revenue.currency,
            self.net_income.currency,
            self.operating_cash_flow.currency,
            self.equity.currency,
        }
        if len(currencies) != 1:
            raise ValueError("a financial period cannot mix currencies")
        if self.available_on < self.period_end:
            raise ValueError("financial data cannot be available before period end")
        if self.diluted_shares <= 0:
            raise ValueError("diluted shares must be positive")

    @property
    def currency(self) -> str:
        return self.revenue.currency

    @property
    def net_margin(self) -> Decimal | None:
        if self.revenue.amount == 0:
            return None
        return self.net_income.amount / self.revenue.amount

    @property
    def earnings_per_share(self) -> Money:
        return Money(self.net_income.amount / self.diluted_shares, self.currency)


@dataclass(frozen=True, slots=True)
class FinancialResearch:
    periods: tuple[FinancialPeriod, ...]
    findings: tuple[str, ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.periods:
            raise ValueError("financial research requires at least one period")
        if not self.findings:
            raise ValueError("financial research requires findings")
        ordered = tuple(sorted(self.periods, key=lambda item: item.period_end, reverse=True))
        object.__setattr__(self, "periods", ordered)

    @property
    def latest(self) -> FinancialPeriod:
        return self.periods[0]

    @property
    def data_as_of(self) -> date:
        return max(period.available_on for period in self.periods)
