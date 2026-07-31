"""
Global Market Data Models — unified enums and request/response types.

LXL QuantAxis v5.6 — Data Infrastructure Layer
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


# ============================================================
# Market & Asset Enums
# ============================================================

class Market(Enum):
    """Standardized market identifiers."""
    CN = "CN"       # China A-shares
    US = "US"       # United States
    HK = "HK"       # Hong Kong
    GLOBAL = "GLOBAL"  # Cross-market / global indices

    @classmethod
    def from_string(cls, s: str) -> "Market":
        """Convert legacy market strings to standard Market enum.

        Accepts: 'A股','CN','中国'→CN; '美股','US','美国'→US; '港股','HK','香港'→HK;
                 'GLOBAL','全球'→GLOBAL; '指数'→CN (index of china by default).
        """
        if not isinstance(s, str):
            raise DataSourceError(f"Invalid market type: {s!r} (expected str)")
        s = s.strip().upper()
        if s in ("CN", "A股", "A", "中国", "CHINA", "SH", "SZ"):
            return cls.CN
        if s in ("US", "美股", "美国", "USA", "AMERICA", "NYSE", "NASDAQ"):
            return cls.US
        if s in ("HK", "港股", "香港", "HONG KONG", "HKG"):
            return cls.HK
        if s in ("GLOBAL", "全球", "WORLD"):
            return cls.GLOBAL
        # Fallback: treat "指数" as CN index
        if s in ("指数", "INDEX"):
            return cls.CN
        raise DataSourceError(f"Unknown market: {s!r}. Expected: CN/US/HK/GLOBAL")

    def timezone(self) -> str:
        """Return IANA timezone for this market."""
        return {
            Market.CN: "Asia/Shanghai",
            Market.HK: "Asia/Hong_Kong",
            Market.US: "America/New_York",
            Market.GLOBAL: "UTC",
        }[self]

    def currency(self) -> str:
        """Return ISO 4217 currency code."""
        return {
            Market.CN: "CNY",
            Market.HK: "HKD",
            Market.US: "USD",
            Market.GLOBAL: "USD",
        }[self]

    def label(self) -> str:
        """Human-readable label."""
        return {
            Market.CN: "China A-Share",
            Market.HK: "Hong Kong",
            Market.US: "United States",
            Market.GLOBAL: "Global",
        }[self]


class AssetType(Enum):
    """Standardized asset type identifiers."""
    STOCK = "STOCK"
    ETF = "ETF"
    INDEX = "INDEX"
    MACRO = "MACRO"

    @classmethod
    def from_string(cls, s: str) -> "AssetType":
        """Convert legacy asset type strings.

        Accepts: 'stock','股票','个股'→STOCK; 'etf','ETF'→ETF;
                 'index','指数'→INDEX; 'macro','宏观'→MACRO.
        """
        if not isinstance(s, str):
            raise DataSourceError(f"Invalid asset type: {s!r} (expected str)")
        s = s.strip().upper()
        if s in ("STOCK", "股票", "个股", "EQUITY"):
            return cls.STOCK
        if s in ("ETF",):
            return cls.ETF
        if s in ("INDEX", "指数", "INDICES"):
            return cls.INDEX
        if s in ("MACRO", "宏观", "MACROECONOMIC"):
            return cls.MACRO
        raise DataSourceError(f"Unknown asset type: {s!r}. Expected: STOCK/ETF/INDEX/MACRO")


# ============================================================
# Custom Exceptions
# ============================================================

class DataSourceError(Exception):
    """Raised when a data source fails or returns invalid data."""

class DataValidationError(Exception):
    """Raised when data fails integrity checks."""

class CacheError(Exception):
    """Raised when cache operations fail."""

class SymbolResolutionError(DataSourceError):
    """Raised when a symbol cannot be resolved to a market/provider."""


# ============================================================
# Data Request Model
# ============================================================

@dataclass
class DataRequest:
    """Unified data request for all markets and asset types.

    All fields except `symbol` have sensible defaults.
    """

    symbol: str
    market: Market = Market.CN
    asset_type: AssetType = AssetType.STOCK
    start_date: str = "2020-01-01"
    end_date: Optional[str] = None
    interval: str = "1d"           # 1d, 1wk, 1mo
    adjust: str = "qfq"            # qfq (forward-adjusted), hfq (backward), or ''
    use_cache: bool = True
    min_lookback_days: int = 250   # Auto-extend start_date for indicator warmup

    def __post_init__(self):
        if self.end_date is None:
            self.end_date = datetime.now().strftime("%Y-%m-%d")
        # Validate interval
        if self.interval not in ("1d", "1wk", "1mo", "5m", "15m", "30m", "1h"):
            raise DataSourceError(f"Unsupported interval: {self.interval}")


# ============================================================
# Standardized Output Columns
# ============================================================

# Standard equity/ETF/index output columns
EQUITY_COLUMNS = [
    "date", "open", "high", "low", "close", "adjusted_close",
    "volume", "symbol", "market", "currency",
]

# Standard macro output columns
MACRO_COLUMNS = [
    "date", "value", "series_id", "source",
]


# ============================================================
# Market metadata helpers
# ============================================================

MARKET_TIMEZONE = {m: m.timezone() for m in Market}
MARKET_CURRENCY = {m: m.currency() for m in Market}

# Symbol suffix mapping for MarketDataAdapter compatibility
SUFFIX_MAP = {
    ".SH": Market.CN, ".SZ": Market.CN,
    ".HK": Market.HK, ".US": Market.US,
    ".CSI": Market.CN,
}
