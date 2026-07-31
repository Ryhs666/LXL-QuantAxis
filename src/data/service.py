"""
MarketDataService — unified entry point for all market data.

Routes requests to the appropriate provider based on market and asset type.
Provides both the new DataRequest-based API and legacy compatibility wrappers.
"""

from typing import Optional, List, Dict
import pandas as pd

from src.data.models import (
    DataRequest, DataSourceError, DataValidationError,
    Market, AssetType, SymbolResolutionError,
)
from src.data.cache import DataCache, cache as global_cache, get_data_dir
from src.data.validators import validate_ohlcv, validate_macro, check_data_integrity
from src.data.providers.base import BaseProvider
from src.data.providers.china import ChinaProvider, china_provider
from src.data.providers.yahoo import YahooProvider, yahoo_provider
from src.data.providers.macro import MacroProvider, macro_provider, MACRO_SERIES


class MarketDataService:
    """Unified market data service.

    Routes DataRequest objects to the correct provider and handles
    caching, validation, and error normalization.

    Usage:
        svc = MarketDataService()

        # New API
        request = DataRequest(symbol="600519", market=Market.CN)
        df = svc.get_history(request)

        # Macro data
        macro_req = DataRequest(symbol="us_10y_yield", market=Market.US,
                                asset_type=AssetType.MACRO)
        df = svc.get_history(macro_req)
    """

    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._cache = global_cache

        # Register default providers
        self.register_provider(china_provider)
        self.register_provider(yahoo_provider)
        self.register_provider(macro_provider)

    # ---- Provider management ----

    def register_provider(self, provider: BaseProvider):
        """Register a data provider."""
        self._providers[provider.name] = provider

    def get_provider(self, name: str) -> Optional[BaseProvider]:
        """Get a registered provider by name."""
        return self._providers.get(name)

    def _resolve_provider(self, request: DataRequest) -> BaseProvider:
        """Find the best provider for a request."""
        # Try each provider in registration order
        for provider in self._providers.values():
            if provider.can_serve(request):
                return provider

        raise SymbolResolutionError(
            f"No provider registered for market={request.market.value} "
            f"asset_type={request.asset_type.value}. "
            f"Registered providers: {list(self._providers.keys())}"
        )

    # ---- Core API ----

    def get_history(self, request: DataRequest) -> pd.DataFrame:
        """Fetch historical data for any supported market/asset combination.

        Args:
            request: DataRequest with symbol, market, asset_type, dates, etc.

        Returns:
            Standardized OHLCV or macro DataFrame.

        Raises:
            SymbolResolutionError: No provider for this market/asset.
            DataSourceError: Provider failed to fetch data.
            DataValidationError: Returned data failed validation.
        """
        provider = self._resolve_provider(request)

        # Auto-extend start date for indicator warmup
        if request.min_lookback_days > 0 and request.asset_type != AssetType.MACRO:
            from datetime import datetime, timedelta
            try:
                target = datetime.strptime(request.start_date, "%Y-%m-%d")
                extended = target - timedelta(days=request.min_lookback_days * 2)
                if extended < target:
                    request.start_date = extended.strftime("%Y-%m-%d")
            except Exception:
                pass

        # Fetch
        try:
            df = provider.get_history(request)
        except (DataSourceError, DataValidationError):
            raise
        except Exception as e:
            raise DataSourceError(
                f"[MarketDataService] Provider '{provider.name}' failed "
                f"for {request.symbol}: {e}"
            )

        # Run integrity checks (non-fatal warnings)
        if request.asset_type != AssetType.MACRO:
            warnings = check_data_integrity(df, request.symbol)
            if warnings:
                for w in warnings:
                    import logging
                    logging.getLogger("quantaxis.data").warning(w)

        return df

    # ---- Convenience ----

    def get_equity(self, symbol: str, market: Market = Market.CN,
                   start_date: str = "2020-01-01", end_date: str = None,
                   use_cache: bool = True) -> pd.DataFrame:
        """Shortcut for equity data."""
        return self.get_history(DataRequest(
            symbol=symbol, market=market, asset_type=AssetType.STOCK,
            start_date=start_date, end_date=end_date, use_cache=use_cache,
        ))

    def get_index(self, symbol: str, market: Market = Market.CN,
                  start_date: str = "2020-01-01", end_date: str = None,
                  use_cache: bool = True) -> pd.DataFrame:
        """Shortcut for index data."""
        return self.get_history(DataRequest(
            symbol=symbol, market=market, asset_type=AssetType.INDEX,
            start_date=start_date, end_date=end_date, use_cache=use_cache,
        ))

    def get_macro(self, series_id: str, start_date: str = "2000-01-01",
                  end_date: str = None, use_cache: bool = True) -> pd.DataFrame:
        """Shortcut for macro data."""
        return self.get_history(DataRequest(
            symbol=series_id, market=Market.US, asset_type=AssetType.MACRO,
            start_date=start_date, end_date=end_date, use_cache=use_cache,
            min_lookback_days=0,
        ))

    def get_multi(self, requests: List[DataRequest]) -> Dict[str, pd.DataFrame]:
        """Batch fetch multiple requests. Returns {symbol: DataFrame}."""
        results = {}
        errors = []
        for req in requests:
            try:
                df = self.get_history(req)
                results[req.symbol] = df
            except Exception as e:
                errors.append({"symbol": req.symbol, "error": str(e)})
        if errors:
            import logging
            log = logging.getLogger("quantaxis.data")
            for err in errors:
                log.warning(f"Batch fetch failed: {err['symbol']}: {err['error']}")
        return results

    # ---- Cache access ----

    def cache_summary(self) -> pd.DataFrame:
        """Return summary of all cached data."""
        return self._cache.summary()

    def clear_cache(self, days: int = 30):
        """Clear cache files older than N days."""
        self._cache.clear_expired(days)


# ============================================================
# Global service instance
# ============================================================

service = MarketDataService()


# ============================================================
# Legacy compatibility wrappers
# ============================================================

def get_data(symbol: str, market: str = "A股",
             start_date: str = "2020-01-01", end_date: str = None,
             use_cache: bool = True, min_lookback_days: int = 250) -> pd.DataFrame:
    """[COMPAT] Legacy get_data — wraps MarketDataService.

    Accepts old market strings ('A股','美股','港股','指数') and
    routes to the new provider architecture.
    """
    # Map legacy market strings
    market_str_to_enum = {
        "A股": Market.CN, "美股": Market.US, "港股": Market.HK,
    }

    if market in market_str_to_enum:
        mkt = market_str_to_enum[market]
        asset = AssetType.STOCK
    elif market == "指数":
        mkt = Market.CN
        asset = AssetType.INDEX
    else:
        # Try Market.from_string as fallback
        try:
            mkt = Market.from_string(market)
            asset = AssetType.STOCK
        except DataSourceError:
            raise ValueError(f"不支持的市场: {market}，可选: A股/美股/港股/指数")

    return service.get_history(DataRequest(
        symbol=symbol, market=mkt, asset_type=asset,
        start_date=start_date, end_date=end_date,
        use_cache=use_cache, min_lookback_days=min_lookback_days,
    ))


def get_a_stock(symbol: str, start_date: str = "2020-01-01",
                end_date: str = None, period: str = "daily",
                use_cache: bool = True) -> pd.DataFrame:
    """[COMPAT] Legacy get_a_stock."""
    return service.get_equity(
        symbol, Market.CN, start_date=start_date,
        end_date=end_date, use_cache=use_cache,
    )


def get_us_stock(symbol: str, start_date: str = "2020-01-01",
                 end_date: str = None, use_cache: bool = True) -> pd.DataFrame:
    """[COMPAT] Legacy get_us_stock."""
    return service.get_equity(
        symbol, Market.US, start_date=start_date,
        end_date=end_date, use_cache=use_cache,
    )


def get_hk_stock(symbol: str, start_date: str = "2020-01-01",
                 end_date: str = None, use_cache: bool = True) -> pd.DataFrame:
    """[COMPAT] Legacy get_hk_stock."""
    return service.get_equity(
        symbol, Market.HK, start_date=start_date,
        end_date=end_date, use_cache=use_cache,
    )


def get_index_data(symbol: str, start_date: str = "2020-01-01",
                   end_date: str = None, use_cache: bool = True) -> pd.DataFrame:
    """[COMPAT] Legacy get_index_data."""
    return service.get_index(
        symbol, Market.CN, start_date=start_date,
        end_date=end_date, use_cache=use_cache,
    )


def download_watchlist(watchlist: list, start_date: str = "2020-01-01",
                       verbose: bool = True) -> Dict[str, pd.DataFrame]:
    """[COMPAT] Legacy download_watchlist.

    watchlist format: [{"symbol": "600519", "market": "A股", "name": "茅台"}, ...]
    """
    results = {}
    errors = []
    total = len(watchlist)

    for i, item in enumerate(watchlist, 1):
        symbol = item["symbol"]
        market_str = item["market"]
        name = item.get("name", symbol)
        key = f"{market_str}:{symbol}"

        if verbose:
            print(f"  [{i}/{total}] {market_str} {symbol} {name} ...", end=" ")

        try:
            df = get_data(symbol, market_str, start_date=start_date, use_cache=True)
            results[key] = df
            if verbose:
                print(f"OK ({len(df)} 条)")
        except Exception as e:
            errors.append({"symbol": symbol, "market": market_str, "error": str(e)})
            if verbose:
                print(f"FAIL: {e}")

    if verbose and errors:
        print(f"\n  {len(errors)} 个失败:")
        for e in errors:
            print(f"    - {e['market']} {e['symbol']}: {e['error']}")

    return results


def get_default_watchlist() -> list:
    """[COMPAT] Legacy get_default_watchlist."""
    return [
        {"symbol": "000300", "market": "指数", "name": "沪深300"},
        {"symbol": "000016", "market": "指数", "name": "上证50"},
        {"symbol": "000905", "market": "指数", "name": "中证500"},
        {"symbol": "600519", "market": "A股", "name": "贵州茅台"},
        {"symbol": "000858", "market": "A股", "name": "五粮液"},
        {"symbol": "601318", "market": "A股", "name": "中国平安"},
        {"symbol": "600036", "market": "A股", "name": "招商银行"},
        {"symbol": "601398", "market": "A股", "name": "工商银行"},
        {"symbol": "000333", "market": "A股", "name": "美的集团"},
        {"symbol": "600276", "market": "A股", "name": "恒瑞医药"},
        {"symbol": "300750", "market": "A股", "name": "宁德时代"},
        {"symbol": "002415", "market": "A股", "name": "海康威视"},
        {"symbol": "600900", "market": "A股", "name": "长江电力"},
        {"symbol": "601899", "market": "A股", "name": "紫金矿业"},
        {"symbol": "300059", "market": "A股", "name": "东方财富"},
        {"symbol": "688981", "market": "A股", "name": "中芯国际"},
    ]


def download_all_default(start_date: str = "2020-01-01",
                         verbose: bool = True) -> Dict[str, pd.DataFrame]:
    """[COMPAT] Legacy download_all_default."""
    return download_watchlist(get_default_watchlist(), start_date=start_date, verbose=verbose)


def get_data_summary() -> pd.DataFrame:
    """[COMPAT] Legacy get_data_summary — now uses cache summary."""
    return service.cache_summary()
