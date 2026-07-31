"""
YahooProvider — US equities, HK equities, international indices, and ETFs via yfinance.

Handles:
  - US stocks (e.g., AAPL, GOOGL, MSFT)
  - US ETFs (e.g., SPY, QQQ)
  - Hong Kong stocks (e.g., 0700.HK, 9988.HK)
  - International indices (e.g., ^GSPC, ^DJI, ^IXIC)
"""

import pandas as pd
import numpy as np
from datetime import datetime

from src.data.models import DataRequest, DataSourceError, Market, AssetType
from src.data.providers.base import BaseProvider
from src.data.cache import cache as global_cache
from src.data.validators import validate_ohlcv


class YahooProvider(BaseProvider):
    """Provider for US, HK, and international market data via yfinance."""

    name = "yahoo"
    supported_markets = (Market.US, Market.HK, Market.GLOBAL)
    supported_asset_types = (AssetType.STOCK, AssetType.ETF, AssetType.INDEX)

    def get_history(self, request: DataRequest) -> pd.DataFrame:
        """Fetch historical data from Yahoo Finance.

        Symbol format expected:
          - US: raw ticker (AAPL, GOOGL)
          - HK: xxxx.HK (0700.HK, 9988.HK)
          - Global indices: ^GSPC, ^DJI
        """
        # Check cache
        if request.use_cache:
            cached = global_cache.load(
                request.symbol, request.market, request.asset_type, request.interval
            )
            if cached is not None:
                cached_start = str(cached["date"].min())[:10]
                cached_end = str(cached["date"].max())[:10]
                if cached_start <= request.start_date and cached_end >= request.end_date:
                    mask = (cached["date"] >= request.start_date) & (cached["date"] <= request.end_date)
                    return cached[mask].reset_index(drop=True)

        # Fetch
        df = self._fetch(request)

        # Validate
        self._validate_response(df, request.symbol)
        df = validate_ohlcv(df, request.symbol, request.market)

        # Cache
        if request.use_cache and len(df) > 0:
            global_cache.save(df, request.symbol, request.market,
                            request.asset_type, request.interval)

        return df

    def _fetch(self, request: DataRequest) -> pd.DataFrame:
        """Core fetch logic using yfinance."""
        try:
            import yfinance as yf
        except ImportError:
            raise DataSourceError(
                "[YahooProvider] yfinance is required. Install: pip install yfinance"
            )

        symbol = self._resolve_symbol(request)
        try:
            ticker = yf.Ticker(symbol)
            # Map interval to yfinance format
            interval_map = {"1d": "1d", "1wk": "1wk", "1mo": "1mo"}
            yf_interval = interval_map.get(request.interval, "1d")

            df = ticker.history(
                start=request.start_date,
                end=request.end_date,
                interval=yf_interval,
            )
        except Exception as e:
            raise DataSourceError(
                f"[YahooProvider] Failed to fetch {symbol}: {e}. "
                f"Verify the symbol is correct and yfinance is accessible."
            )

        if df.empty:
            raise DataSourceError(
                f"[YahooProvider] Empty response for {symbol}. "
                f"The symbol may be delisted, invalid, or have no data in the requested range."
            )

        # Normalize
        df = df.reset_index()
        df = df.rename(columns={
            "Date": "date", "Datetime": "date",
            "Open": "open", "High": "high",
            "Low": "low", "Close": "close",
            "Volume": "volume",
        })

        # Remove timezone from date
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)

        return df

    def _resolve_symbol(self, request: DataRequest) -> str:
        """Resolve symbol to yfinance-compatible format."""
        symbol = request.symbol.strip()

        if request.market == Market.HK:
            # Ensure .HK suffix
            if not symbol.endswith(".HK"):
                symbol = symbol.zfill(4) + ".HK" if symbol.isdigit() else symbol + ".HK"
            return symbol

        if request.market == Market.US:
            return symbol.upper()

        # GLOBAL: pass through (e.g., ^GSPC, EURUSD=X)
        return symbol

    def get_info(self, symbol: str) -> dict:
        """Get basic info for a symbol via yfinance."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            return {
                "symbol": symbol,
                "name": info.get("longName", info.get("shortName", "")),
                "market": info.get("market", ""),
                "currency": info.get("currency", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
            }
        except Exception:
            return {"symbol": symbol, "name": "", "market": "", "currency": ""}


# Singleton
yahoo_provider = YahooProvider()
