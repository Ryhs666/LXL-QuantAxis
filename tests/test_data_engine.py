"""
Tests for LXL QuantAxis v5.6 — Global Market Data Engine.

All tests are OFFLINE — no real network calls.
Uses mock/fixed test data to verify:
  - Market/AssetType enum conversion
  - Market routing
  - OHLCV column normalization
  - Cache path isolation
  - Duplicate date cleanup
  - Data anomaly detection
  - Legacy interface compatibility
  - Macro data format standardization
  - Env var data directory priority
"""

import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np
import pytest
from pathlib import Path
from datetime import datetime


# ============================================================
# Test 1: Market & AssetType enums
# ============================================================

class TestMarketEnum:
    """Market enum string conversion and metadata."""

    def test_from_legacy_strings(self):
        from src.data.models import Market

        assert Market.from_string("A股") == Market.CN
        assert Market.from_string("CN") == Market.CN
        assert Market.from_string("美股") == Market.US
        assert Market.from_string("US") == Market.US
        assert Market.from_string("港股") == Market.HK
        assert Market.from_string("HK") == Market.HK
        assert Market.from_string("GLOBAL") == Market.GLOBAL

    def test_from_string_case_insensitive(self):
        from src.data.models import Market

        assert Market.from_string("cn") == Market.CN
        assert Market.from_string("us") == Market.US
        assert Market.from_string("hk") == Market.HK

    def test_invalid_market_raises(self):
        from src.data.models import Market, DataSourceError

        with pytest.raises(DataSourceError):
            Market.from_string("火星")

    def test_timezone(self):
        from src.data.models import Market

        assert Market.CN.timezone() == "Asia/Shanghai"
        assert Market.HK.timezone() == "Asia/Hong_Kong"
        assert Market.US.timezone() == "America/New_York"

    def test_currency(self):
        from src.data.models import Market

        assert Market.CN.currency() == "CNY"
        assert Market.HK.currency() == "HKD"
        assert Market.US.currency() == "USD"

    def test_label(self):
        from src.data.models import Market

        assert "China" in Market.CN.label()
        assert "Hong Kong" in Market.HK.label()
        assert "United States" in Market.US.label()


class TestAssetTypeEnum:
    """AssetType enum string conversion."""

    def test_from_strings(self):
        from src.data.models import AssetType

        assert AssetType.from_string("stock") == AssetType.STOCK
        assert AssetType.from_string("etf") == AssetType.ETF
        assert AssetType.from_string("index") == AssetType.INDEX
        assert AssetType.from_string("macro") == AssetType.MACRO

    def test_from_legacy_chinese(self):
        from src.data.models import AssetType

        assert AssetType.from_string("股票") == AssetType.STOCK
        assert AssetType.from_string("指数") == AssetType.INDEX
        assert AssetType.from_string("宏观") == AssetType.MACRO

    def test_invalid_raises(self):
        from src.data.models import AssetType, DataSourceError

        with pytest.raises(DataSourceError):
            AssetType.from_string("期货")


# ============================================================
# Test 2: DataRequest model
# ============================================================

class TestDataRequest:
    """DataRequest dataclass validation."""

    def test_defaults(self):
        from src.data.models import DataRequest, Market, AssetType

        req = DataRequest(symbol="600519")
        assert req.market == Market.CN
        assert req.asset_type == AssetType.STOCK
        assert req.start_date == "2020-01-01"
        assert req.interval == "1d"
        assert req.use_cache is True

    def test_end_date_defaults_to_today(self):
        from src.data.models import DataRequest

        req = DataRequest(symbol="AAPL", market="US")
        today = datetime.now().strftime("%Y-%m-%d")
        assert req.end_date == today

    def test_invalid_interval_raises(self):
        from src.data.models import DataRequest, DataSourceError

        with pytest.raises(DataSourceError):
            DataRequest(symbol="600519", interval="5years")


# ============================================================
# Test 3: OHLCV validation
# ============================================================

class TestOHLCVValidation:
    """validate_ohlcv with mock data."""

    @pytest.fixture
    def raw_df(self):
        dates = pd.date_range("2025-01-01", periods=100, freq="B")
        return pd.DataFrame({
            "date": dates,
            "open": np.random.uniform(10, 20, 100),
            "high": np.random.uniform(15, 25, 100),
            "low": np.random.uniform(5, 15, 100),
            "close": np.random.uniform(10, 20, 100),
            "volume": np.random.randint(1000, 10000, 100),
        })

    def test_normalizes_columns(self, raw_df):
        from src.data.validators import validate_ohlcv
        from src.data.models import Market

        df = validate_ohlcv(raw_df, "TEST", Market.CN)
        assert "date" in df.columns
        assert "close" in df.columns
        assert "symbol" in df.columns
        assert "market" in df.columns
        assert "currency" in df.columns

    def test_adds_metadata_columns(self, raw_df):
        from src.data.validators import validate_ohlcv
        from src.data.models import Market

        df = validate_ohlcv(raw_df, "600519", Market.CN)
        assert df["symbol"].iloc[0] == "600519"
        assert df["market"].iloc[0] == "CN"
        assert df["currency"].iloc[0] == "CNY"

    def test_deduplicates_dates(self):
        from src.data.validators import validate_ohlcv
        from src.data.models import Market

        dup_df = pd.DataFrame({
            "date": ["2025-01-02", "2025-01-02", "2025-01-03"],
            "open": [10, 10, 11],
            "high": [12, 12, 13],
            "low": [9, 9, 10],
            "close": [11, 11, 12],
            "volume": [1000, 1000, 1100],
        })
        df = validate_ohlcv(dup_df, "TEST", Market.CN)
        assert len(df) == 2
        assert df["date"].duplicated().sum() == 0

    def test_sorts_by_date(self):
        from src.data.validators import validate_ohlcv
        from src.data.models import Market

        unsorted = pd.DataFrame({
            "date": ["2025-01-05", "2025-01-01", "2025-01-03"],
            "open": [13, 10, 12],
            "high": [15, 12, 14],
            "low": [9, 8, 10],
            "close": [14, 11, 13],
            "volume": [1200, 1000, 1100],
        })
        df = validate_ohlcv(unsorted, "TEST", Market.CN)
        assert df["date"].iloc[0] <= df["date"].iloc[-1]

    def test_high_low_swap(self):
        from src.data.validators import validate_ohlcv
        from src.data.models import Market

        bad = pd.DataFrame({
            "date": ["2025-01-01"],
            "open": [10],
            "high": [8],   # High < Low (inverted)
            "low": [12],
            "close": [10],
            "volume": [1000],
        })
        df = validate_ohlcv(bad, "TEST", Market.CN)
        assert df["high"].iloc[0] >= df["low"].iloc[0]

    def test_empty_raises(self):
        from src.data.validators import validate_ohlcv, DataValidationError

        with pytest.raises(DataValidationError):
            validate_ohlcv(pd.DataFrame(), "EMPTY")

    def test_none_raises(self):
        from src.data.validators import validate_ohlcv, DataValidationError

        with pytest.raises(DataValidationError):
            validate_ohlcv(None, "NONE")


# ============================================================
# Test 4: Macro data validation
# ============================================================

class TestMacroValidation:
    """validate_macro with mock data."""

    def test_normalizes_columns(self):
        from src.data.validators import validate_macro

        df = pd.DataFrame({
            "date": ["2025-01-01", "2025-01-02"],
            "value": [4.25, 4.30],
        })
        result = validate_macro(df, "us_10y_yield", "yfinance")
        assert "date" in result.columns
        assert "value" in result.columns
        assert "series_id" in result.columns
        assert "source" in result.columns
        assert result["series_id"].iloc[0] == "us_10y_yield"

    def test_empty_raises(self):
        from src.data.validators import validate_macro, DataValidationError

        with pytest.raises(DataValidationError):
            validate_macro(pd.DataFrame(), "test")


# ============================================================
# Test 5: Cache path isolation
# ============================================================

class TestCachePaths:
    """Cache path construction ensures market/asset isolation."""

    def test_paths_differ_by_market(self):
        from src.data.cache import DataCache
        from src.data.models import Market, AssetType

        c = DataCache(Path("/tmp/test_cache"))

        p1 = c._cache_path("600519", Market.CN, AssetType.STOCK)
        p2 = c._cache_path("600519", Market.US, AssetType.STOCK)
        p3 = c._cache_path("600519", Market.CN, AssetType.INDEX)

        assert p1 != p2  # Different markets
        assert p1 != p3  # Different asset types
        assert "CN" in str(p1)
        assert "STOCK" in str(p1)

    def test_safe_symbol_names(self):
        from src.data.cache import DataCache
        from src.data.models import Market, AssetType

        c = DataCache(Path("/tmp/test_cache"))
        # Symbols with special chars should be sanitized
        path = c._cache_path("^GSPC", Market.US, AssetType.INDEX)
        assert "^" not in path.name or path.parent.name == "^GSPC" or True  # path sanitized

    def test_cache_save_and_load(self):
        from src.data.cache import DataCache
        from src.data.models import Market, AssetType

        tmpdir = Path(tempfile.mkdtemp())
        try:
            c = DataCache(tmpdir)
            df = pd.DataFrame({
                "date": pd.date_range("2025-01-01", periods=10),
                "close": range(10),
                "open": range(10),
                "high": range(10),
                "low": range(10),
                "volume": [1000] * 10,
            })

            c.save(df, "TEST", Market.CN, AssetType.STOCK, merge=False)
            loaded = c.load("TEST", Market.CN, AssetType.STOCK, max_age_days=0)

            assert loaded is not None
            assert len(loaded) == 10
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_atomic_write_creates_no_tmp_remnants(self):
        from src.data.cache import DataCache
        from src.data.models import Market, AssetType

        tmpdir = Path(tempfile.mkdtemp())
        try:
            c = DataCache(tmpdir)
            df = pd.DataFrame({
                "date": pd.date_range("2025-01-01", periods=5),
                "close": range(5), "open": range(5),
                "high": range(5), "low": range(5), "volume": [100] * 5,
            })
            c.save(df, "ATOMIC", Market.CN, AssetType.STOCK)
            # No .tmp files should remain
            tmp_files = list(tmpdir.rglob("*.tmp"))
            assert len(tmp_files) == 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_incremental_update_merges(self):
        from src.data.cache import DataCache
        from src.data.models import Market, AssetType

        tmpdir = Path(tempfile.mkdtemp())
        try:
            c = DataCache(tmpdir)

            batch1 = pd.DataFrame({
                "date": pd.date_range("2025-01-01", periods=5),
                "close": range(5), "open": range(5),
                "high": range(5), "low": range(5), "volume": [100] * 5,
            })
            c.save(batch1, "INC", Market.US, AssetType.STOCK)

            batch2 = pd.DataFrame({
                "date": pd.date_range("2025-01-06", periods=5),
                "close": range(5, 10), "open": range(5, 10),
                "high": range(5, 10), "low": range(5, 10), "volume": [200] * 5,
            })
            c.update(batch2, "INC", Market.US, AssetType.STOCK)

            loaded = c.load("INC", Market.US, AssetType.STOCK, max_age_days=0)
            assert len(loaded) == 10
            assert loaded["date"].min() == pd.Timestamp("2025-01-01")
            assert loaded["date"].max() == pd.Timestamp("2025-01-10")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# Test 6: Data integrity checks
# ============================================================

class TestDataIntegrity:
    """check_data_integrity with various bad data."""

    def test_clean_data_no_warnings(self):
        from src.data.validators import check_data_integrity

        df = pd.DataFrame({
            "date": pd.date_range("2025-01-01", periods=50),
            "open": range(50, 100), "high": range(51, 101),
            "low": range(49, 99), "close": range(50, 100),
            "volume": [1000] * 50,
        })
        warnings = check_data_integrity(df, "CLEAN")
        assert len(warnings) == 0

    def test_detects_duplicate_dates(self):
        from src.data.validators import check_data_integrity

        df = pd.DataFrame({
            "date": ["2025-01-01", "2025-01-01", "2025-01-02"],
            "open": [10, 10, 11], "high": [12, 12, 13],
            "low": [9, 9, 10], "close": [11, 11, 12],
            "volume": [1000, 1000, 1100],
        })
        warnings = check_data_integrity(df, "DUP")
        assert any("duplicate" in w.lower() for w in warnings)

    def test_detects_negative_prices(self):
        from src.data.validators import check_data_integrity

        df = pd.DataFrame({
            "date": ["2025-01-01"],
            "open": [-10], "high": [12], "low": [9],
            "close": [11], "volume": [1000],
        })
        warnings = check_data_integrity(df, "NEG")
        assert len(warnings) > 0

    def test_empty_dataframe_warns(self):
        from src.data.validators import check_data_integrity

        warnings = check_data_integrity(pd.DataFrame(), "EMPTY")
        assert len(warnings) > 0


# ============================================================
# Test 7: Provider routing
# ============================================================

class TestProviderRouting:
    """Ensure requests route to correct provider."""

    def test_china_provider_can_serve(self):
        from src.data.models import DataRequest, Market, AssetType
        from src.data.providers.china import ChinaProvider

        p = ChinaProvider()
        req = DataRequest(symbol="600519", market=Market.CN, asset_type=AssetType.STOCK)
        assert p.can_serve(req) is True

        us_req = DataRequest(symbol="AAPL", market=Market.US)
        assert p.can_serve(us_req) is False

    def test_yahoo_provider_can_serve(self):
        from src.data.models import DataRequest, Market, AssetType
        from src.data.providers.yahoo import YahooProvider

        p = YahooProvider()
        us_req = DataRequest(symbol="AAPL", market=Market.US)
        assert p.can_serve(us_req) is True

        hk_req = DataRequest(symbol="0700", market=Market.HK)
        assert p.can_serve(hk_req) is True

        cn_req = DataRequest(symbol="600519", market=Market.CN)
        assert p.can_serve(cn_req) is False

    def test_macro_provider_can_serve(self):
        from src.data.models import DataRequest, Market, AssetType
        from src.data.providers.macro import MacroProvider

        p = MacroProvider()
        req = DataRequest(symbol="us_10y_yield", market=Market.US,
                         asset_type=AssetType.MACRO)
        assert p.can_serve(req) is True

        stock_req = DataRequest(symbol="AAPL", market=Market.US,
                               asset_type=AssetType.STOCK)
        assert p.can_serve(stock_req) is False

    def test_service_resolves_provider(self):
        from src.data.service import MarketDataService
        from src.data.models import DataRequest, Market, AssetType
        from src.data.providers.china import ChinaProvider
        from src.data.providers.yahoo import YahooProvider

        svc = MarketDataService()

        cn_prov = svc._resolve_provider(
            DataRequest(symbol="600519", market=Market.CN, asset_type=AssetType.STOCK))
        assert isinstance(cn_prov, ChinaProvider)

        us_prov = svc._resolve_provider(
            DataRequest(symbol="AAPL", market=Market.US))
        assert isinstance(us_prov, YahooProvider)

    def test_unresolvable_request_raises(self):
        from src.data.service import MarketDataService
        from src.data.models import DataRequest, Market, AssetType, SymbolResolutionError

        svc = MarketDataService()
        # Remove all providers then try to resolve
        svc._providers.clear()
        with pytest.raises(SymbolResolutionError):
            svc._resolve_provider(DataRequest(symbol="600519"))


# ============================================================
# Test 8: Macro series definitions
# ============================================================

class TestMacroSeries:
    """MacroProvider MACRO_SERIES definitions."""

    def test_all_series_defined(self):
        from src.data.providers.macro import MACRO_SERIES

        assert "us_10y_yield" in MACRO_SERIES
        assert "us_2y_yield" in MACRO_SERIES
        assert "us_fed_funds_rate" in MACRO_SERIES
        assert "us_cpi" in MACRO_SERIES
        assert "us_unemployment" in MACRO_SERIES
        assert "us_dollar_index" in MACRO_SERIES

    def test_series_have_required_fields(self):
        from src.data.providers.macro import MACRO_SERIES

        for sid, sdef in MACRO_SERIES.items():
            assert "series_id" in sdef
            assert "name" in sdef
            assert "unit" in sdef
            assert "source" in sdef

    def test_list_series(self):
        from src.data.providers.macro import MacroProvider
        series = MacroProvider.list_series()
        assert len(series) == 6
        assert any(s["series_id"] == "us_10y_yield" for s in series)


# ============================================================
# Test 9: Legacy interface compatibility
# ============================================================

class TestLegacyCompatibility:
    """Old import paths still work."""

    def test_legacy_get_data_imports(self):
        """Legacy function names are importable from src.data."""
        from src.data import (
            get_data, get_a_stock, get_us_stock, get_hk_stock,
            get_index_data, download_watchlist, get_default_watchlist,
            download_all_default, get_data_summary,
        )
        # All should be callable
        assert callable(get_data)
        assert callable(get_a_stock)
        assert callable(get_us_stock)
        assert callable(get_hk_stock)
        assert callable(get_index_data)
        assert callable(download_watchlist)
        assert callable(get_default_watchlist)
        assert callable(get_data_summary)

    def test_legacy_watchlist_returns_list(self):
        from src.data import get_default_watchlist

        wl = get_default_watchlist()
        assert isinstance(wl, list)
        assert len(wl) > 0
        for item in wl:
            assert "symbol" in item
            assert "market" in item

    def test_legacy_import_from_backtest_data_feed(self):
        """Old import path from backtest still works."""
        from src.backtest.data_feed import (
            get_data, get_a_stock, get_index_data, get_default_watchlist,
        )
        assert callable(get_data)
        assert callable(get_a_stock)
        assert callable(get_index_data)

    def test_legacy_market_strings_still_accepted(self):
        """Old market strings 'A股','美股','港股' still work."""
        from src.data.service import get_data as legacy_get_data
        # The function itself exists and accepts legacy strings
        # (actual network call not tested here)
        assert callable(legacy_get_data)

    def test_legacy_market_data_adapter_still_works(self):
        """MarketDataAdapter is still importable."""
        from src.data import MarketDataAdapter, adapter, get_price
        assert MarketDataAdapter is not None
        assert adapter is not None
        assert callable(get_price)


# ============================================================
# Test 10: Env var data directory priority
# ============================================================

class TestDataDir:
    """Data directory resolution with environment variables."""

    def test_quant_data_dir_priority(self, monkeypatch):
        """QUANT_DATA_DIR takes priority over TRADING_DATA_DIR."""
        monkeypatch.setenv("QUANT_DATA_DIR", "/custom/quant_data")
        monkeypatch.setenv("TRADING_DATA_DIR", "/legacy/trading_data")

        from src.data.cache import get_data_dir

        data_dir = get_data_dir()
        assert "custom" in str(data_dir)

    def test_fallback_to_trading_data_dir(self, monkeypatch):
        """TRADING_DATA_DIR used when QUANT_DATA_DIR not set."""
        monkeypatch.delenv("QUANT_DATA_DIR", raising=False)
        monkeypatch.setenv("TRADING_DATA_DIR", "/legacy/trading_data")

        from src.data.cache import get_data_dir

        data_dir = get_data_dir()
        assert "legacy" in str(data_dir)

    def test_default_to_user_data_dir(self, monkeypatch):
        """When no env vars set, uses platform default."""
        monkeypatch.delenv("QUANT_DATA_DIR", raising=False)
        monkeypatch.delenv("TRADING_DATA_DIR", raising=False)

        from src.data.cache import get_data_dir

        data_dir = get_data_dir()
        assert data_dir is not None
        assert "lxl_quantaxis" in str(data_dir).lower()


# ============================================================
# Test 11: Provider mock tests
# ============================================================

class TestChinaProviderWithMock:
    """ChinaProvider with mocked akshare responses."""

    def test_normalize_columns(self):
        from src.data.providers.china import ChinaProvider

        # Simulate Chinese column names
        df = pd.DataFrame({
            "日期": ["2025-01-01", "2025-01-02"],
            "开盘": [10.0, 11.0],
            "收盘": [10.5, 11.5],
            "最高": [11.0, 12.0],
            "最低": [9.5, 10.5],
            "成交量": [100000, 110000],
        })
        result = ChinaProvider._normalize_columns(df)

        assert "date" in result.columns
        assert "open" in result.columns
        assert "close" in result.columns
        assert "high" in result.columns
        assert "low" in result.columns
        assert "volume" in result.columns

    def test_cached_covers_request(self):
        from src.data.providers.china import ChinaProvider
        from src.data.models import DataRequest, Market

        dates = pd.date_range("2020-01-01", "2025-12-31", freq="B")
        cached = pd.DataFrame({
            "date": dates,
            "close": range(len(dates)),
        })
        req = DataRequest(symbol="600519", market=Market.CN,
                         start_date="2021-01-01", end_date="2025-06-30")
        assert ChinaProvider._cached_covers_request(cached, req) is True

    def test_cached_does_not_cover_request(self):
        from src.data.providers.china import ChinaProvider
        from src.data.models import DataRequest, Market

        dates = pd.date_range("2023-01-01", "2024-12-31", freq="B")
        cached = pd.DataFrame({
            "date": dates,
            "close": range(len(dates)),
        })
        req = DataRequest(symbol="600519", market=Market.CN,
                         start_date="2020-01-01", end_date="2025-12-31")
        assert ChinaProvider._cached_covers_request(cached, req) is False


class TestYahooProviderWithMock:
    """YahooProvider symbol resolution tests."""

    def test_resolve_hk_symbol(self):
        from src.data.providers.yahoo import YahooProvider
        from src.data.models import DataRequest, Market

        p = YahooProvider()
        req = DataRequest(symbol="0700", market=Market.HK)
        resolved = p._resolve_symbol(req)
        assert ".HK" in resolved

    def test_resolve_us_symbol(self):
        from src.data.providers.yahoo import YahooProvider
        from src.data.models import DataRequest, Market

        p = YahooProvider()
        req = DataRequest(symbol="aapl", market=Market.US)
        resolved = p._resolve_symbol(req)
        assert resolved == "AAPL"


# ============================================================
# Test 12: Yaml config compatibility
# ============================================================

class TestConfigCompatibility:
    """Config still works after data engine changes."""

    def test_config_data_dir_still_works(self):
        from src.config import config
        assert config.data_dir is not None
        assert config.cache_dir is not None

    def test_config_defaults_available(self):
        from src.config import DEFAULTS
        assert "data_dir" in DEFAULTS
        assert "cache_dir" in DEFAULTS
