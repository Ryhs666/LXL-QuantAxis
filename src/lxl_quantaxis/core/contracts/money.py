"""Exact monetary value object based on Decimal."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import TypeAlias

AmountInput: TypeAlias = Decimal | int | str
SUPPORTED_CURRENCIES = frozenset({"AUD", "CAD", "CHF", "CNY", "EUR", "GBP", "HKD", "JPY", "SGD", "USD"})


def validate_currency(currency: object) -> str:
    """Return a canonical ISO 4217 code supported by the platform."""

    if not isinstance(currency, str):
        raise ValueError("currency must be a string")
    normalized = currency.strip().upper()
    if normalized not in SUPPORTED_CURRENCIES:
        raise ValueError(f"unsupported ISO 4217 currency: {currency!r}")
    return normalized


def _decimal(value: object) -> Decimal:
    if isinstance(value, (bool, float)):
        raise TypeError("money amount must use Decimal, int, or str; float is not accepted")
    if not isinstance(value, (Decimal, int, str)):
        raise TypeError("money amount must use Decimal, int, or str")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"invalid money amount: {value!r}") from exc
    if not amount.is_finite():
        raise ValueError("money amount must be finite")
    return amount


@dataclass(frozen=True, slots=True)
class Money:
    """An exact amount paired with a canonical currency."""

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", _decimal(self.amount))
        object.__setattr__(self, "currency", validate_currency(self.currency))

    @classmethod
    def of(cls, amount: AmountInput, currency: str) -> Money:
        return cls(amount=_decimal(amount), currency=currency)

    def _require_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(f"currency mismatch: {self.currency} != {other.currency}")

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            raise TypeError("money can only be added to money")
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            raise TypeError("money can only be subtracted from money")
        self._require_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def multiply(self, multiplier: AmountInput) -> Money:
        return Money(self.amount * _decimal(multiplier), self.currency)

    def to_dict(self) -> dict[str, str]:
        return {"amount": str(self.amount), "currency": self.currency}

    @classmethod
    def from_dict(cls, value: dict[str, str]) -> Money:
        return cls.of(value["amount"], value["currency"])
