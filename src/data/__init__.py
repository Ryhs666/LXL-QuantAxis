"""
LXL QuantAxis v5.6 — Global Market Data Engine

Unified data infrastructure for multi-market, multi-asset quantitative research.

New API (recommended):
    from src.data import MarketDataService, DataRequest, Market, AssetType
    svc = MarketDataService()
    df = svc.get_history(DataRequest(symbol="600519", market=Market.CN))

Legacy API (backward compatible):
    from src.data import get_data, get_a_stock, get_us_stock
    df = get_data("600519", "A股")

Modules:
  models.py       — Market, AssetType enums, DataRequest, exceptions
  service.py      — MarketDataService + legacy compatibility wrappers
  cache.py        — Hierarchical, atomic-write cache
  validators.py   — Data validation and normalization
  providers/      — ChinaProvider, YahooProvider, MacroProvider
"""

# --- New framework ---
from src.data.models import (
    Market,
    AssetType,
    DataRequest,
    DataSourceError,
    DataValidationError,
    CacheError,
    SymbolResolutionError,
    EQUITY_COLUMNS,
    MACRO_COLUMNS,
    MARKET_TIMEZONE,
    MARKET_CURRENCY,
)
from src.data.cache import DataCache, cache, get_data_dir, DATA_DIR, CACHE_DIR
from src.data.validators import validate_ohlcv, validate_macro, check_data_integrity
from src.data.service import (
    MarketDataService,
    service,
    # Legacy compatibility wrappers
    get_data,
    get_a_stock,
    get_us_stock,
    get_hk_stock,
    get_index_data,
    download_watchlist,
    get_default_watchlist,
    download_all_default,
    get_data_summary,
)
from src.data.providers import (
    BaseProvider,
    ChinaProvider,
    YahooProvider,
    MacroProvider,
)

# --- Legacy re-exports (existing modules stay importable) ---
from src.data import integrity          # DataIntegrityChecker
from src.data.MarketDataAdapter import (  # MarketDataAdapter + adapter
    MarketDataAdapter,
    adapter,
    get_price,
)

# --- Macro series listing ---
from src.data.providers.macro import MACRO_SERIES, macro_provider

__all__ = [
    # Models
    "Market", "AssetType", "DataRequest",
    "DataSourceError", "DataValidationError", "CacheError",
    "SymbolResolutionError",
    "EQUITY_COLUMNS", "MACRO_COLUMNS",
    "MARKET_TIMEZONE", "MARKET_CURRENCY",
    # Cache
    "DataCache", "cache", "get_data_dir", "DATA_DIR", "CACHE_DIR",
    # Validators
    "validate_ohlcv", "validate_macro", "check_data_integrity",
    # Service
    "MarketDataService", "service",
    # Providers
    "BaseProvider", "ChinaProvider", "YahooProvider", "MacroProvider",
    # Macro
    "MACRO_SERIES", "macro_provider",
    # Legacy
    "get_data", "get_a_stock", "get_us_stock", "get_hk_stock",
    "get_index_data", "download_watchlist", "get_default_watchlist",
    "download_all_default", "get_data_summary",
    "MarketDataAdapter", "adapter", "get_price",
    "integrity",
]
