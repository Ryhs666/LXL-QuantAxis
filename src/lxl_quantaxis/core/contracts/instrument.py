"""Canonical instrument identifiers for supported equity markets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class Market(StrEnum):
    """Stable machine-readable market codes."""

    CN = "CN"
    HK = "HK"
    US = "US"
    INDEX = "INDEX"

    @classmethod
    def parse(cls, value: str | Market) -> Market:
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise ValueError("market must be a string or Market")
        try:
            return cls(value.strip().upper())
        except ValueError as exc:
            raise ValueError(f"unsupported market: {value!r}") from exc


def _normalize_symbol(symbol: str, market: Market) -> str:
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbol must be a non-empty string")
    normalized = symbol.strip().upper()

    if market in {Market.CN, Market.INDEX}:
        if re.fullmatch(r"\d{6}", normalized) is None:
            raise ValueError(f"{market.value} symbol must contain exactly 6 digits")
        return normalized
    if market is Market.HK:
        if re.fullmatch(r"\d{1,5}", normalized) is None:
            raise ValueError("HK symbol must contain between 1 and 5 digits")
        return normalized.zfill(5)
    if re.fullmatch(r"[A-Z]{1,5}(?:[.-][A-Z]{1,3})?", normalized) is None:
        raise ValueError("US symbol has an invalid ticker format")
    return normalized


@dataclass(frozen=True, slots=True, order=True)
class Instrument:
    """A canonical market and symbol pair."""

    market: Market
    symbol: str

    def __post_init__(self) -> None:
        market = Market.parse(self.market)
        object.__setattr__(self, "market", market)
        object.__setattr__(self, "symbol", _normalize_symbol(self.symbol, market))

    @classmethod
    def create(cls, symbol: str, market: Market | str) -> Instrument:
        return cls(market=Market.parse(market), symbol=symbol)

    @classmethod
    def parse(cls, value: str) -> Instrument:
        if not isinstance(value, str) or ":" not in value:
            raise ValueError("instrument must use MARKET:SYMBOL format")
        market, symbol = value.split(":", 1)
        return cls.create(symbol=symbol, market=market)

    def to_dict(self) -> dict[str, str]:
        return {"market": self.market.value, "symbol": self.symbol}

    @classmethod
    def from_dict(cls, value: dict[str, str]) -> Instrument:
        return cls.create(symbol=value["symbol"], market=value["market"])

    def __str__(self) -> str:
        return f"{self.market.value}:{self.symbol}"
