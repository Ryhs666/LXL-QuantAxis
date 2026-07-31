"""
ChinaProvider — A-share stocks and China indices via AKShare/Sina/EastMoney.

Handles:
  - A-share stocks (Shanghai 6xxxxx, Shenzhen 0xxxxx/3xxxxx)
  - China indices (CSI 300, SSE 50, CSI 500, etc.)
  - China ETFs

Data sources (tried in order):
  1. Sina Finance (fast, stable)
  2. East Money (fallback)
"""

import time
import pandas as pd
from datetime import datetime
from typing import Optional

from src.data.models import DataRequest, DataSourceError, Market, AssetType
from src.data.providers.base import BaseProvider
from src.data.cache import cache as global_cache
from src.data.validators import validate_ohlcv


class ChinaProvider(BaseProvider):
    """Provider for China A-share equities, indices, and ETFs."""

    name = "china"
    supported_markets = (Market.CN,)
    supported_asset_types = (AssetType.STOCK, AssetType.ETF, AssetType.INDEX)

    # Known China indices
    INDEX_MAP = {
        "000300": "沪深300",
        "000016": "上证50",
        "000905": "中证500",
        "000852": "中证1000",
        "399001": "深证成指",
        "399006": "创业板指",
        "000688": "科创50",
    }

    def get_history(self, request: DataRequest) -> pd.DataFrame:
        """Fetch A-share or China index historical data.

        Routes to the appropriate fetcher based on asset_type.
        """
        # Check cache
        if request.use_cache:
            cached = global_cache.load(
                request.symbol, request.market, request.asset_type, request.interval
            )
            if cached is not None and self._cached_covers_request(cached, request):
                return self._slice_cached(cached, request)

        # Fetch based on asset type
        if request.asset_type == AssetType.INDEX:
            df = self._fetch_index(request)
        else:
            df = self._fetch_stock(request)

        # Validate
        self._validate_response(df, request.symbol)
        df = validate_ohlcv(df, request.symbol, request.market)

        # Cache
        if request.use_cache and len(df) > 0:
            global_cache.save(df, request.symbol, request.market,
                            request.asset_type, request.interval)

        return df

    # ---- Stock fetching ----

    def _fetch_stock(self, request: DataRequest) -> pd.DataFrame:
        """Fetch A-share stock data.

        Sources tried in order:
          1. Sina Finance (stock_zh_a_daily)
          2. East Money (stock_zh_a_hist)
        """
        symbol = request.symbol
        start = request.start_date.replace("-", "")
        end = request.end_date.replace("-", "")

        df = None
        last_error = None

        # Source 1: Sina
        try:
            exchange = f"sh{symbol}" if symbol.startswith(("6", "9")) else f"sz{symbol}"
            import akshare as ak
            df = ak.stock_zh_a_daily(
                symbol=exchange, start_date=start, end_date=end,
                adjust=request.adjust or "qfq",
            )
        except Exception as e:
            last_error = e

        # Source 2: East Money
        if df is None or df.empty:
            try:
                import akshare as ak
                df = ak.stock_zh_a_hist(
                    symbol=symbol, period=request.interval,
                    start_date=start, end_date=end,
                    adjust=request.adjust or "qfq",
                )
            except Exception as e:
                last_error = e

        if df is None or df.empty:
            raise DataSourceError(
                f"[ChinaProvider] All sources failed for {symbol}: {last_error}"
            )

        return self._normalize_columns(df)

    # ---- Index fetching ----

    def _fetch_index(self, request: DataRequest) -> pd.DataFrame:
        """Fetch China index data."""
        symbol = request.symbol
        try:
            import akshare as ak

            # Determine exchange prefix
            if symbol.startswith("000") or symbol.startswith("399"):
                exchange_code = f"sh{symbol}" if symbol.startswith("000") else f"sz{symbol}"
            else:
                exchange_code = f"sh{symbol}"

            df = ak.stock_zh_index_daily(symbol=exchange_code)

            if df is None or df.empty:
                raise DataSourceError(
                    f"[ChinaProvider] No index data for {symbol}. "
                    f"Check that the index code is valid."
                )

            return self._normalize_columns(df)

        except ImportError:
            raise DataSourceError(
                "[ChinaProvider] akshare is required for China index data. "
                "Install: pip install akshare"
            )

    # ---- Column normalization ----

    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize Chinese data source column names to standard OHLCV."""
        rename_map = {}
        for src, dst in [
            ("日期", "date"), ("开盘", "open"), ("收盘", "close"),
            ("最高", "high"), ("最低", "low"), ("成交量", "volume"),
            ("成交额", "amount"),
        ]:
            if src in df.columns:
                rename_map[src] = dst
        if rename_map:
            df = df.rename(columns=rename_map)
        return df

    # ---- Cache helpers ----

    @staticmethod
    def _cached_covers_request(cached: pd.DataFrame, request: DataRequest) -> bool:
        """Check if cached data covers the requested date range."""
        if cached is None or "date" not in cached.columns:
            return False
        cached_start = str(cached["date"].min())[:10]
        cached_end = str(cached["date"].max())[:10]
        return cached_start <= request.start_date and cached_end >= request.end_date

    @staticmethod
    def _slice_cached(cached: pd.DataFrame, request: DataRequest) -> pd.DataFrame:
        """Slice cached data to requested date range."""
        mask = (cached["date"] >= request.start_date) & (cached["date"] <= request.end_date)
        return cached[mask].reset_index(drop=True)


# Singleton
china_provider = ChinaProvider()
