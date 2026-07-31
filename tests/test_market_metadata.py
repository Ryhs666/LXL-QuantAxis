"""Tests for market metadata and calendar utilities."""
import os
import sys
import unittest
from unittest.mock import patch
from datetime import date, datetime
import zoneinfo

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.backtest.market_metadata import (
    MarketMetadata,
    MarketCalendar,
    get_market_metadata,
    get_market_timezone,
    get_market_calendar,
)
from src.backtest.data_feed import get_data


# ============================================================
# 辅助
# ============================================================

def _make_sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=5),
        "open": [1.0] * 5,
        "high": [1.5] * 5,
        "low": [0.9] * 5,
        "close": [1.2] * 5,
        "volume": [1000] * 5,
    })


# ============================================================
# 测试 1-6: 市场元数据
# ============================================================

class TestMarketMetadata(unittest.TestCase):
    """测试四个市场的元数据及时区别名。"""

    def test_a_share_metadata(self):
        m = get_market_metadata("A股")
        self.assertEqual(m.market, "A股")
        self.assertEqual(m.timezone, "Asia/Shanghai")
        self.assertEqual(m.currency, "CNY")
        self.assertEqual(m.calendar, "CN")

    def test_us_metadata(self):
        m = get_market_metadata("美股")
        self.assertEqual(m.market, "美股")
        self.assertEqual(m.timezone, "America/New_York")
        self.assertEqual(m.currency, "USD")
        self.assertEqual(m.calendar, "US")

    def test_hk_metadata(self):
        m = get_market_metadata("港股")
        self.assertEqual(m.market, "港股")
        self.assertEqual(m.timezone, "Asia/Hong_Kong")
        self.assertEqual(m.currency, "HKD")
        self.assertEqual(m.calendar, "HK")

    def test_index_metadata(self):
        m = get_market_metadata("指数")
        self.assertEqual(m.market, "指数")
        self.assertEqual(m.timezone, "Asia/Shanghai")
        self.assertEqual(m.currency, "CNY")
        self.assertEqual(m.calendar, "CN_INDEX")

    # ---- 别名 ----

    def test_alias_a_share(self):
        for alias in ["A", "CN", "CHINA", "cn"]:
            with self.subTest(alias=alias):
                m = get_market_metadata(alias)
                self.assertEqual(m.market, "A股")

    def test_alias_us(self):
        for alias in ["US", "USA", "us"]:
            with self.subTest(alias=alias):
                m = get_market_metadata(alias)
                self.assertEqual(m.market, "美股")

    def test_alias_hk(self):
        for alias in ["HK", "HONGKONG", "hk"]:
            with self.subTest(alias=alias):
                m = get_market_metadata(alias)
                self.assertEqual(m.market, "港股")

    def test_alias_index(self):
        for alias in ["INDEX", "IDX", "index"]:
            with self.subTest(alias=alias):
                m = get_market_metadata(alias)
                self.assertEqual(m.market, "指数")

    # ---- 不可变 ----

    def test_metadata_is_frozen(self):
        m = get_market_metadata("A股")
        with self.assertRaises(Exception):
            m.timezone = "other"  # dataclass frozen

    # ---- 非法市场 ----

    def test_unknown_market_raises(self):
        with self.assertRaises(ValueError):
            get_market_metadata("火星")

    # ---- 时区 ----

    def test_timezone_creates_zoneinfo(self):
        for market in ["A股", "美股", "港股", "指数"]:
            with self.subTest(market=market):
                tz = get_market_timezone(market)
                self.assertIsInstance(tz, zoneinfo.ZoneInfo)

    def test_timezone_values(self):
        self.assertEqual(str(get_market_timezone("A股")), "Asia/Shanghai")
        self.assertEqual(str(get_market_timezone("美股")), "America/New_York")
        self.assertEqual(str(get_market_timezone("港股")), "Asia/Hong_Kong")
        self.assertEqual(str(get_market_timezone("指数")), "Asia/Shanghai")


# ============================================================
# 测试 7-14: 交易日历
# ============================================================

class TestMarketCalendar(unittest.TestCase):
    """测试 MarketCalendar 的交易日判断。"""

    def setUp(self):
        self.cal = get_market_calendar("A股")

    # ---- 周一至周五 ----

    def test_weekdays_are_trading_days(self):
        """周一至周五为基础交易日。"""
        # 2024-07-29 Mon, 07-30 Tue, 07-31 Wed, 08-01 Thu, 08-02 Fri
        for d in ["2024-07-29", "2024-07-30", "2024-07-31", "2024-08-01", "2024-08-02"]:
            with self.subTest(date=d):
                self.assertTrue(self.cal.is_trading_day(d))

    def test_weekends_are_not_trading_days(self):
        """周六、周日不是交易日。"""
        self.assertFalse(self.cal.is_trading_day("2024-08-03"))  # Saturday
        self.assertFalse(self.cal.is_trading_day("2024-08-04"))  # Sunday

    # ---- 注入假日 ----

    def test_injected_holiday_not_trading_day(self):
        cal = get_market_calendar("A股", holidays=["2024-08-01"])
        self.assertFalse(cal.is_trading_day("2024-08-01"))

    def test_holidays_accept_date_objects(self):
        cal = get_market_calendar("A股", holidays=[date(2024, 8, 1)])
        self.assertFalse(cal.is_trading_day("2024-08-01"))

    def test_holidays_accept_datetime_objects(self):
        cal = get_market_calendar("A股", holidays=[datetime(2024, 8, 1, 10, 30)])
        self.assertFalse(cal.is_trading_day("2024-08-01"))

    # ---- next_trading_day ----

    def test_next_trading_day_skips_weekend(self):
        """周五之后的下一个交易日是周一。"""
        nxt = self.cal.next_trading_day("2024-08-02")  # Friday
        self.assertEqual(nxt, date(2024, 8, 5))  # Monday

    def test_next_trading_day_skips_injected_holiday(self):
        """注入假日后跳到下一个交易日。"""
        # Wed 2024-07-31 is a holiday, next after Tue 07-30 should be Thu 08-01
        cal = get_market_calendar("A股", holidays=["2024-07-31"])
        nxt = cal.next_trading_day("2024-07-30")  # Tuesday
        self.assertEqual(nxt, date(2024, 8, 1))  # Thursday (Wed is holiday)

    def test_next_trading_day_excludes_input_day(self):
        """next_trading_day 不包含输入当天。"""
        nxt = self.cal.next_trading_day("2024-08-01")  # Thursday
        self.assertEqual(nxt, date(2024, 8, 2))  # Friday, not Thursday

    # ---- previous_trading_day ----

    def test_previous_trading_day_skips_weekend(self):
        """周一之前的上一个交易日是周五。"""
        prev = self.cal.previous_trading_day("2024-08-05")  # Monday
        self.assertEqual(prev, date(2024, 8, 2))  # Friday

    def test_previous_trading_day_excludes_input_day(self):
        """previous_trading_day 不包含输入当天。"""
        prev = self.cal.previous_trading_day("2024-08-02")  # Friday
        self.assertEqual(prev, date(2024, 8, 1))  # Thursday, not Friday

    # ---- 输入类型 ----

    def test_accepts_date_input(self):
        self.assertTrue(self.cal.is_trading_day(date(2024, 7, 31)))

    def test_accepts_datetime_input(self):
        self.assertTrue(self.cal.is_trading_day(datetime(2024, 7, 31, 15, 0)))

    def test_accepts_string_input(self):
        self.assertTrue(self.cal.is_trading_day("2024-07-31"))

    # ---- 非法输入 ----

    def test_invalid_string_format_raises(self):
        with self.assertRaises(ValueError):
            self.cal.is_trading_day("07/31/2024")

    def test_invalid_type_raises(self):
        with self.assertRaises(TypeError):
            self.cal.is_trading_day(42)

    # ---- 市场属性 ----

    def test_calendar_market_property(self):
        cal = get_market_calendar("cn")
        self.assertEqual(cal.market, "A股")


# ============================================================
# 测试 15-18: get_data attrs
# ============================================================

class TestGetDataAttrs(unittest.TestCase):
    """测试 get_data() 返回的 DataFrame.attrs 元数据。"""

    def setUp(self):
        self.mock_df = _make_sample_df()

    @patch("src.backtest.data_feed.get_a_stock")
    def test_attrs_present_on_return(self, mock_fn):
        """get_data 返回的 DataFrame 应包含 attrs 元数据。"""
        mock_fn.return_value = self.mock_df.copy()
        df = get_data("600519", "A股", min_lookback_days=0)
        self.assertIn("symbol", df.attrs)
        self.assertIn("market", df.attrs)
        self.assertIn("timezone", df.attrs)
        self.assertIn("currency", df.attrs)
        self.assertIn("calendar", df.attrs)
        self.assertIn("provider", df.attrs)

    @patch("src.backtest.data_feed.get_a_stock")
    def test_a_share_attrs(self, mock_fn):
        mock_fn.return_value = self.mock_df.copy()
        df = get_data("sh600519", "A股", min_lookback_days=0)
        self.assertEqual(df.attrs["symbol"], "600519")
        self.assertEqual(df.attrs["market"], "A股")
        self.assertEqual(df.attrs["timezone"], "Asia/Shanghai")
        self.assertEqual(df.attrs["currency"], "CNY")
        self.assertEqual(df.attrs["calendar"], "CN")
        self.assertEqual(df.attrs["provider"], "akshare")

    @patch("src.backtest.data_feed.get_us_stock")
    def test_us_attrs(self, mock_fn):
        mock_fn.return_value = self.mock_df.copy()
        df = get_data("aapl", "us", min_lookback_days=0)
        self.assertEqual(df.attrs["symbol"], "AAPL")
        self.assertEqual(df.attrs["market"], "美股")
        self.assertEqual(df.attrs["timezone"], "America/New_York")
        self.assertEqual(df.attrs["currency"], "USD")
        self.assertEqual(df.attrs["calendar"], "US")
        self.assertEqual(df.attrs["provider"], "yfinance")

    @patch("src.backtest.data_feed.get_hk_stock")
    def test_hk_attrs(self, mock_fn):
        mock_fn.return_value = self.mock_df.copy()
        df = get_data("0700.HK", "hk", min_lookback_days=0)
        self.assertEqual(df.attrs["symbol"], "00700")
        self.assertEqual(df.attrs["market"], "港股")
        self.assertEqual(df.attrs["timezone"], "Asia/Hong_Kong")
        self.assertEqual(df.attrs["currency"], "HKD")
        self.assertEqual(df.attrs["calendar"], "HK")
        self.assertEqual(df.attrs["provider"], "akshare")

    @patch("src.backtest.data_feed.get_index_data")
    def test_index_attrs(self, mock_fn):
        mock_fn.return_value = self.mock_df.copy()
        df = get_data("sh000300", "index", min_lookback_days=0)
        self.assertEqual(df.attrs["symbol"], "000300")
        self.assertEqual(df.attrs["market"], "指数")
        self.assertEqual(df.attrs["timezone"], "Asia/Shanghai")
        self.assertEqual(df.attrs["currency"], "CNY")
        self.assertEqual(df.attrs["calendar"], "CN_INDEX")
        self.assertEqual(df.attrs["provider"], "akshare")

    @patch("src.backtest.data_feed.get_a_stock")
    def test_date_column_unchanged(self, mock_fn):
        """attrs 不修改 date 列的类型和内容。"""
        mock_fn.return_value = self.mock_df.copy()
        df = get_data("600519", "A股", min_lookback_days=0)
        # date 列不应有时区
        self.assertIsNone(df["date"].dt.tz)
        # 内容不变
        expected_dates = list(self.mock_df["date"])
        actual_dates = list(df["date"])
        self.assertEqual(actual_dates, expected_dates)

    @patch("src.backtest.data_feed.get_a_stock")
    def test_returns_same_dataframe_object(self, mock_fn):
        """get_data 返回原始 DataFrame 对象（非数据的深拷贝），只是增加了 attrs。"""
        original = self.mock_df.copy()
        mock_fn.return_value = original
        df = get_data("600519", "A股", min_lookback_days=0)
        self.assertIs(df, original)

    @patch("src.backtest.data_feed.get_a_stock")
    def test_data_values_unchanged(self, mock_fn):
        """OHLCV 数据值不变。"""
        mock_fn.return_value = self.mock_df.copy()
        df = get_data("600519", "A股", min_lookback_days=0)
        pd.testing.assert_frame_equal(
            df[["date", "open", "high", "low", "close", "volume"]],
            self.mock_df,
        )


if __name__ == "__main__":
    unittest.main()
