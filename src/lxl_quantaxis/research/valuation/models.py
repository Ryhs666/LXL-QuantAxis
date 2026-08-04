"""Valuation contracts with explicit monetary units."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from src.lxl_quantaxis.core.contracts.money import Money


class ValuationMethod(StrEnum):
    FORWARD_PE = "forward_pe"


class ValuationUnit(StrEnum):
    PER_SHARE = "currency_per_share"


@dataclass(frozen=True, slots=True)
class ValuationEstimate:
    method: ValuationMethod
    fair_value: Money
    unit: ValuationUnit
    data_as_of: date
    assumptions: tuple[str, ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.fair_value.amount < 0:
            raise ValueError("fair value cannot be negative")
        if not self.assumptions:
            raise ValueError("valuation assumptions cannot be empty")


def forward_pe_valuation(
    *,
    earnings_per_share: Money,
    target_multiple: Decimal,
    data_as_of: date,
    evidence_ids: tuple[str, ...],
) -> ValuationEstimate:
    """Calculate a per-share value; EPS is always a currency-per-share input."""

    if target_multiple <= 0:
        raise ValueError("target P/E multiple must be positive")
    return ValuationEstimate(
        method=ValuationMethod.FORWARD_PE,
        fair_value=earnings_per_share.multiply(target_multiple),
        unit=ValuationUnit.PER_SHARE,
        data_as_of=data_as_of,
        assumptions=(f"target P/E: {target_multiple}",),
        evidence_ids=evidence_ids,
    )
