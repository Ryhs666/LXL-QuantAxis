"""
MacroProvider — macroeconomic time series data.

Supported series:
  - US 10-Year Treasury Yield (^TNX)
  - US 2-Year Treasury Yield (^IRX-equivalent via yfinance)
  - Federal Funds Rate (via FRED if available, else yfinance ^IRX)
  - CPI (US Consumer Price Index, via yfinance or AKShare macro)
  - Unemployment Rate (via yfinance or AKShare macro)
  - US Dollar Index (DX-Y.NYB via yfinance)

All macro data is returned in standardized format:
  date, value, series_id, source
"""

import pandas as pd
import numpy as np
from datetime import datetime

from src.data.models import DataRequest, DataSourceError, Market, AssetType
from src.data.providers.base import BaseProvider
from src.data.cache import cache as global_cache
from src.data.validators import validate_macro


# ---- Macro series definitions ----

MACRO_SERIES = {
    "us_10y_yield": {
        "series_id": "us_10y_yield",
        "name": "US 10-Year Treasury Yield",
        "yahoo_symbol": "^TNX",
        "unit": "%",
        "source": "yfinance",
    },
    "us_2y_yield": {
        "series_id": "us_2y_yield",
        "name": "US 2-Year Treasury Yield",
        "yahoo_symbol": "2YY=F",    # 2-Year T-Note futures as proxy
        "unit": "%",
        "source": "yfinance",
    },
    "us_fed_funds_rate": {
        "series_id": "us_fed_funds_rate",
        "name": "Federal Funds Rate",
        "yahoo_symbol": "^IRX",      # 13-week T-bill as rate proxy
        "unit": "%",
        "source": "yfinance",
    },
    "us_cpi": {
        "series_id": "us_cpi",
        "name": "US Consumer Price Index",
        "yahoo_symbol": "CPIAUCSL",  # Not available via yfinance; uses fallback
        "unit": "index",
        "source": "akshare",
    },
    "us_unemployment": {
        "series_id": "us_unemployment",
        "name": "US Unemployment Rate",
        "yahoo_symbol": "UNRATE",    # Not available via yfinance; uses fallback
        "unit": "%",
        "source": "akshare",
    },
    "us_dollar_index": {
        "series_id": "us_dollar_index",
        "name": "US Dollar Index",
        "yahoo_symbol": "DX-Y.NYB",
        "unit": "index",
        "source": "yfinance",
    },
}


class MacroProvider(BaseProvider):
    """Provider for macroeconomic time series.

    Data sources (tried in order):
      1. yfinance (for yields, dollar index)
      2. akshare macro modules (for CPI, unemployment)
      3. Explicit error if all sources fail — never fabricates data.
    """

    name = "macro"
    supported_markets = (Market.US, Market.GLOBAL)
    supported_asset_types = (AssetType.MACRO,)

    def get_history(self, request: DataRequest) -> pd.DataFrame:
        """Fetch macro time series data.

        The request.symbol should be a macro series ID from MACRO_SERIES.
        """
        series_id = request.symbol
        series_def = MACRO_SERIES.get(series_id)

        if series_def is None:
            available = list(MACRO_SERIES.keys())
            raise DataSourceError(
                f"[MacroProvider] Unknown macro series: {series_id!r}. "
                f"Available: {available}"
            )

        # Check cache
        if request.use_cache:
            cached = global_cache.load(
                series_id, Market.US, AssetType.MACRO, request.interval
            )
            if cached is not None:
                return cached

        # Fetch
        df = self._fetch_series(series_def, request)

        # Validate
        if df is None or df.empty:
            raise DataSourceError(
                f"[MacroProvider] Failed to fetch {series_def['name']} ({series_id}). "
                f"Source '{series_def['source']}' returned no data. "
                f"This data series may require an alternative source."
            )

        df = validate_macro(df, series_id, series_def["source"])

        # Cache
        if request.use_cache and len(df) > 0:
            global_cache.save(df, series_id, Market.US, AssetType.MACRO, request.interval)

        return df

    def _fetch_series(self, series_def: dict, request: DataRequest) -> pd.DataFrame:
        """Dispatch to the appropriate fetch method based on source."""
        source = series_def.get("source", "yfinance")

        if source == "yfinance":
            return self._fetch_yahoo_macro(series_def, request)
        elif source == "akshare":
            return self._fetch_akshare_macro(series_def, request)
        else:
            raise DataSourceError(
                f"[MacroProvider] Unknown source '{source}' for {series_def['series_id']}"
            )

    # ---- yfinance macro ----

    def _fetch_yahoo_macro(self, series_def: dict,
                           request: DataRequest) -> pd.DataFrame:
        """Fetch macro data via yfinance (yields, dollar index, etc.)."""
        yahoo_sym = series_def.get("yahoo_symbol")
        if not yahoo_sym:
            raise DataSourceError(
                f"[MacroProvider] No yfinance symbol defined for {series_def['series_id']}"
            )

        try:
            import yfinance as yf
        except ImportError:
            raise DataSourceError(
                "[MacroProvider] yfinance is required for macro data. "
                "Install: pip install yfinance"
            )

        try:
            ticker = yf.Ticker(yahoo_sym)
            df = ticker.history(
                start=request.start_date,
                end=request.end_date,
                interval="1d",
            )
        except Exception as e:
            raise DataSourceError(
                f"[MacroProvider] yfinance fetch failed for {yahoo_sym}: {e}"
            )

        if df is None or df.empty:
            raise DataSourceError(
                f"[MacroProvider] yfinance returned empty data for {yahoo_sym}. "
                f"The symbol may have been delisted or the data range has no data."
            )

        df = df.reset_index()
        if "Close" in df.columns:
            df["value"] = df["Close"]
        elif "close" in df.columns:
            df["value"] = df["close"]
        else:
            raise DataSourceError(
                f"[MacroProvider] No price column in yfinance response for {yahoo_sym}"
            )

        df["date"] = pd.to_datetime(df["Date"] if "Date" in df.columns else df.index)
        return df[["date", "value"]]

    # ---- akshare macro ----

    def _fetch_akshare_macro(self, series_def: dict,
                             request: DataRequest) -> pd.DataFrame:
        """Fetch macro data via akshare (CPI, unemployment, etc.).

        Uses akshare's macro modules. Different endpoints for different series.
        """
        try:
            import akshare as ak
        except ImportError:
            raise DataSourceError(
                "[MacroProvider] akshare is required for some macro data. "
                "Install: pip install akshare"
            )

        series_id = series_def["series_id"]
        start = request.start_date.replace("-", "")
        end = request.end_date.replace("-", "")

        try:
            if series_id == "us_cpi":
                return self._fetch_us_cpi_akshare(ak, start, end)
            elif series_id == "us_unemployment":
                return self._fetch_us_unemployment_akshare(ak, start, end)
            elif series_id == "us_fed_funds_rate":
                return self._fetch_fed_funds_akshare(ak, start, end)
            else:
                raise DataSourceError(
                    f"[MacroProvider] No akshare fetch method for {series_id}"
                )
        except DataSourceError:
            raise
        except Exception as e:
            raise DataSourceError(
                f"[MacroProvider] akshare fetch failed for {series_id}: {e}"
            )

    @staticmethod
    def _fetch_us_cpi_akshare(ak, start: str, end: str) -> pd.DataFrame:
        """Fetch US CPI from akshare macro module."""
        try:
            df = ak.macro_usa_cpi_monthly()
            if df is not None and not df.empty:
                # Columns vary by akshare version; find date + value columns
                date_col = [c for c in df.columns if '日期' in str(c) or 'date' in str(c).lower()]
                val_col = [c for c in df.columns if '值' in str(c) or 'value' in str(c).lower()
                          or 'cpi' in str(c).lower() or '物价' in str(c)]
                if date_col and val_col:
                    result = pd.DataFrame({
                        "date": pd.to_datetime(df[date_col[0]]),
                        "value": pd.to_numeric(df[val_col[0]], errors="coerce"),
                    })
                    return result.dropna()
        except Exception:
            pass

        raise DataSourceError(
            "[MacroProvider] US CPI data is not available via akshare. "
            "The macro_usa_cpi_monthly endpoint may have changed. "
            "Consider using FRED API or manual data import."
        )

    @staticmethod
    def _fetch_us_unemployment_akshare(ak, start: str, end: str) -> pd.DataFrame:
        """Fetch US unemployment rate from akshare macro module."""
        try:
            df = ak.macro_usa_unemployment_rate()
            if df is not None and not df.empty:
                date_col = [c for c in df.columns if '日期' in str(c) or 'date' in str(c).lower()]
                val_col = [c for c in df.columns if '值' in str(c) or 'value' in str(c).lower()
                          or '失业' in str(c) or 'unemploy' in str(c).lower()]
                if date_col and val_col:
                    result = pd.DataFrame({
                        "date": pd.to_datetime(df[date_col[0]]),
                        "value": pd.to_numeric(df[val_col[0]], errors="coerce"),
                    })
                    return result.dropna()
        except Exception:
            pass

        raise DataSourceError(
            "[MacroProvider] US unemployment data is not available via akshare. "
            "The macro_usa_unemployment_rate endpoint may have changed. "
            "Consider using FRED API or manual data import."
        )

    @staticmethod
    def _fetch_fed_funds_akshare(ak, start: str, end: str) -> pd.DataFrame:
        """Fetch Federal Funds Rate from akshare."""
        try:
            df = ak.macro_usa_interest_rate()
            if df is not None and not df.empty:
                date_col = [c for c in df.columns if '日期' in str(c) or 'date' in str(c).lower()]
                val_col = [c for c in df.columns if '值' in str(c) or 'value' in str(c).lower()
                          or '利率' in str(c) or 'rate' in str(c).lower() or 'interest' in str(c).lower()]
                if date_col and val_col:
                    result = pd.DataFrame({
                        "date": pd.to_datetime(df[date_col[0]]),
                        "value": pd.to_numeric(df[val_col[0]], errors="coerce"),
                    })
                    return result.dropna()
        except Exception:
            pass

        # Fallback: try yfinance ^IRX as proxy
        raise DataSourceError(
            "[MacroProvider] Federal Funds Rate not available via akshare. "
            "The ^IRX (13-week T-bill) via yfinance is used as a rate proxy. "
            "Use series_id='us_fed_funds_rate' which will try yfinance first."
        )

    # ---- Listing ----

    @staticmethod
    def list_series() -> list:
        """Return list of available macro series definitions."""
        return [
            {"series_id": k, "name": v["name"], "unit": v["unit"], "source": v["source"]}
            for k, v in MACRO_SERIES.items()
        ]


# Singleton
macro_provider = MacroProvider()
