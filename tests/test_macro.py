"""Tests for standardized macro data contract."""
import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.backtest.macro import (
    MacroSeriesMetadata,
    MacroDataProvider,
    CallableMacroProvider,
    MacroProviderRegistry,
    normalize_macro_code,
    get_macro_metadata,
    list_macro_series,
    normalize_macro_frame,
    get_macro_data,
)


# ============================================================
# 辅助
# ============================================================

def _make_raw_df() -> pd.DataFrame:
    return pd.DataFrame({
        "date": ["2024-01-15", "2024-02-15", "2024-03-15"],
        "value": [0.3, 0.7, 1.0],
    })


# ============================================================
# 测试 1-3: 指标元数据 + code 标准化
# ============================================================

class TestMacroMetadata(unittest.TestCase):
    """测试 8 个预设指标元数据。"""

    def test_all_eight_codes_present(self):
        codes = list_macro_series()
        self.assertEqual(len(codes), 8)

    def test_cn_cpi_yoy(self):
        m = get_macro_metadata("CN_CPI_YOY")
        self.assertEqual(m.code, "CN_CPI_YOY")
        self.assertEqual(m.name, "中国CPI同比")
        self.assertEqual(m.region, "CN")
        self.assertEqual(m.frequency, "monthly")
        self.assertEqual(m.unit, "percent")

    def test_cn_ppi_yoy(self):
        m = get_macro_metadata("CN_PPI_YOY")
        self.assertEqual(m.name, "中国PPI同比")
        self.assertEqual(m.region, "CN")

    def test_cn_pmi(self):
        m = get_macro_metadata("CN_PMI")
        self.assertEqual(m.name, "中国制造业PMI")
        self.assertEqual(m.unit, "index")

    def test_cn_lpr_1y(self):
        m = get_macro_metadata("CN_LPR_1Y")
        self.assertEqual(m.name, "中国1年期LPR")

    def test_us_cpi_yoy(self):
        m = get_macro_metadata("US_CPI_YOY")
        self.assertEqual(m.region, "US")
        self.assertEqual(m.frequency, "monthly")

    def test_us_fed_funds(self):
        m = get_macro_metadata("US_FED_FUNDS")
        self.assertEqual(m.name, "美国联邦基金利率")

    def test_us_unemployment(self):
        m = get_macro_metadata("US_UNEMPLOYMENT")
        self.assertEqual(m.unit, "percent")

    def test_us_10y_yield(self):
        m = get_macro_metadata("US_10Y_YIELD")
        self.assertEqual(m.frequency, "daily")
        self.assertEqual(m.unit, "percent")

    def test_metadata_is_frozen(self):
        m = get_macro_metadata("CN_CPI_YOY")
        with self.assertRaises(Exception):
            m.code = "OTHER"  # frozen dataclass


class TestNormalizeMacroCode(unittest.TestCase):
    """测试 code 标准化。"""

    def test_lowercase(self):
        self.assertEqual(normalize_macro_code("cn_cpi_yoy"), "CN_CPI_YOY")

    def test_whitespace(self):
        self.assertEqual(normalize_macro_code("  CN_CPI_YOY  "), "CN_CPI_YOY")

    def test_mixed_case(self):
        self.assertEqual(normalize_macro_code("Cn_Cpi_Yoy"), "CN_CPI_YOY")

    def test_none_raises(self):
        with self.assertRaises(ValueError):
            normalize_macro_code(None)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            normalize_macro_code("")

    def test_whitespace_only_raises(self):
        with self.assertRaises(ValueError):
            normalize_macro_code("   ")

    def test_unknown_code_raises(self):
        with self.assertRaises(ValueError):
            normalize_macro_code("JP_GDP_YOY")


class TestListMacroSeries(unittest.TestCase):
    """测试按 region 筛选指标。"""

    def test_all_returns_eight(self):
        self.assertEqual(len(list_macro_series()), 8)

    def test_filter_cn(self):
        cn = list_macro_series("CN")
        self.assertEqual(len(cn), 4)
        for c in cn:
            self.assertTrue(c.startswith("CN_"))

    def test_filter_us(self):
        us = list_macro_series("US")
        self.assertEqual(len(us), 4)
        for c in us:
            self.assertTrue(c.startswith("US_"))

    def test_filter_case_insensitive(self):
        self.assertEqual(list_macro_series("cn"), list_macro_series("CN"))
        self.assertEqual(list_macro_series("us"), list_macro_series("US"))

    def test_filter_whitespace(self):
        self.assertEqual(list_macro_series("  CN  "), list_macro_series("CN"))

    def test_invalid_region_raises(self):
        with self.assertRaises(ValueError):
            list_macro_series("JP")

    def test_empty_region_raises(self):
        with self.assertRaises(ValueError):
            list_macro_series("")

    def test_order_stable(self):
        a = list_macro_series()
        b = list_macro_series()
        self.assertEqual(a, b)


# ============================================================
# 测试 5-15: normalize_macro_frame
# ============================================================

class TestNormalizeMacroFrame(unittest.TestCase):
    """测试 normalize_macro_frame 的各种规则。"""

    def test_missing_date_raises(self):
        df = pd.DataFrame({"value": [1.0]})
        with self.assertRaises(ValueError):
            normalize_macro_frame(df, "CN_CPI_YOY")

    def test_missing_value_raises(self):
        df = pd.DataFrame({"date": ["2024-01-01"]})
        with self.assertRaises(ValueError):
            normalize_macro_frame(df, "CN_CPI_YOY")

    def test_date_converted_to_datetime(self):
        df = pd.DataFrame({"date": ["2024-01-01"], "value": [1.0]})
        result = normalize_macro_frame(df, "CN_CPI_YOY")
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result["date"]))

    def test_value_converted_to_numeric(self):
        df = pd.DataFrame({"date": ["2024-01-01"], "value": ["1.5"]})
        result = normalize_macro_frame(df, "CN_CPI_YOY")
        self.assertEqual(result["value"].iloc[0], 1.5)

    def test_non_numeric_value_raises(self):
        df = pd.DataFrame({"date": ["2024-01-01"], "value": ["not_a_number"]})
        with self.assertRaises(ValueError):
            normalize_macro_frame(df, "CN_CPI_YOY")

    def test_sorted_by_date_ascending(self):
        df = pd.DataFrame({
            "date": ["2024-03-01", "2024-01-01", "2024-02-01"],
            "value": [3.0, 1.0, 2.0],
        })
        result = normalize_macro_frame(df, "CN_CPI_YOY")
        expected_dates = pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"])
        self.assertTrue((result["date"] == expected_dates).all())

    def test_dedup_keeps_last(self):
        df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-01"],
            "value": [1.0, 2.0],
        })
        result = normalize_macro_frame(df, "CN_CPI_YOY")
        self.assertEqual(len(result), 1)
        self.assertEqual(result["value"].iloc[0], 2.0)

    def test_start_date_filter(self):
        df = _make_raw_df()
        result = normalize_macro_frame(df, "CN_CPI_YOY", start_date="2024-02-01")
        self.assertGreaterEqual(result["date"].min(), pd.Timestamp("2024-02-01"))

    def test_end_date_filter(self):
        df = _make_raw_df()
        result = normalize_macro_frame(df, "CN_CPI_YOY", end_date="2024-02-28")
        self.assertLessEqual(result["date"].max(), pd.Timestamp("2024-02-28"))

    def test_invalid_date_range_raises(self):
        df = _make_raw_df()
        with self.assertRaises(ValueError):
            normalize_macro_frame(df, "CN_CPI_YOY", start_date="2024-06-01", end_date="2024-01-01")

    def test_input_not_modified(self):
        df = _make_raw_df()
        original = df.copy()
        normalize_macro_frame(df, "CN_CPI_YOY")
        pd.testing.assert_frame_equal(df, original)

    def test_columns_are_date_and_value(self):
        df = _make_raw_df()
        result = normalize_macro_frame(df, "CN_CPI_YOY")
        self.assertEqual(list(result.columns), ["date", "value"])

    def test_attrs_complete(self):
        df = _make_raw_df()
        result = normalize_macro_frame(df, "CN_CPI_YOY")
        self.assertEqual(result.attrs["code"], "CN_CPI_YOY")
        self.assertEqual(result.attrs["name"], "中国CPI同比")
        self.assertEqual(result.attrs["region"], "CN")
        self.assertEqual(result.attrs["frequency"], "monthly")
        self.assertEqual(result.attrs["unit"], "percent")


# ============================================================
# 测试 16-18: CallableMacroProvider
# ============================================================

class TestCallableMacroProvider(unittest.TestCase):
    """测试 CallableMacroProvider 的参数转发和行为。"""

    def setUp(self):
        self.sample_df = _make_raw_df()

    def test_forwards_parameters(self):
        captured = {}

        def capture(code, start_date, end_date):
            captured["code"] = code
            captured["start_date"] = start_date
            captured["end_date"] = end_date
            return self.sample_df

        p = CallableMacroProvider(name="test", fetcher=capture)
        p.fetch("CN_CPI_YOY", start_date="2024-01-01", end_date="2024-12-31")
        self.assertEqual(captured["code"], "CN_CPI_YOY")
        self.assertEqual(captured["start_date"], "2024-01-01")
        self.assertEqual(captured["end_date"], "2024-12-31")

    def test_returns_dataframe(self):
        p = CallableMacroProvider(
            name="test", fetcher=lambda code, **kw: self.sample_df
        )
        result = p.fetch("CN_CPI_YOY")
        self.assertIsInstance(result, pd.DataFrame)
        self.assertIs(result, self.sample_df)

    def test_default_none_params(self):
        captured = {}

        def capture(code, start_date, end_date):
            captured["start_date"] = start_date
            captured["end_date"] = end_date
            return self.sample_df

        p = CallableMacroProvider(name="test", fetcher=capture)
        p.fetch("CN_CPI_YOY")
        self.assertIsNone(captured["start_date"])
        self.assertIsNone(captured["end_date"])

    def test_non_callable_fetcher_raises(self):
        with self.assertRaises(TypeError):
            CallableMacroProvider(name="bad", fetcher="not_callable")

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            CallableMacroProvider(name="", fetcher=lambda **kw: None)

    def test_name_is_stripped(self):
        p = CallableMacroProvider(name="  MyProvider  ", fetcher=lambda **kw: None)
        self.assertEqual(p.name, "MyProvider")


# ============================================================
# 测试 19: MacroProviderRegistry
# ============================================================

class TestMacroProviderRegistry(unittest.TestCase):
    """测试注册表逻辑。"""

    def setUp(self):
        self.registry = MacroProviderRegistry()
        self.provider = CallableMacroProvider(
            name="test_p", fetcher=lambda **kw: _make_raw_df()
        )

    def test_register_and_get(self):
        self.registry.register(self.provider)
        self.assertIn("test_p", self.registry.names())

    def test_get_by_name(self):
        self.registry.register(self.provider)
        p = self.registry.get("test_p")
        self.assertIs(p, self.provider)

    def test_get_case_and_space_insensitive(self):
        self.registry.register(self.provider)
        p = self.registry.get("  TEST_P  ")
        self.assertIs(p, self.provider)

    def test_duplicate_raises(self):
        self.registry.register(self.provider)
        p2 = CallableMacroProvider(name="test_p", fetcher=lambda **kw: None)
        with self.assertRaises(ValueError):
            self.registry.register(p2)

    def test_replace(self):
        self.registry.register(self.provider)
        p2 = CallableMacroProvider(name="test_p", fetcher=lambda **kw: None)
        self.registry.register(p2, replace=True)
        self.assertIs(self.registry.get("test_p"), p2)

    def test_unknown_name_raises(self):
        with self.assertRaises(ValueError):
            self.registry.get("nonexistent")

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            self.registry.get("")

    def test_non_provider_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.registry.register("not_a_provider")

    def test_names_order_stable(self):
        p_a = CallableMacroProvider(name="a", fetcher=lambda **kw: None)
        p_b = CallableMacroProvider(name="b", fetcher=lambda **kw: None)
        self.registry.register(p_a)
        self.registry.register(p_b)
        self.assertEqual(self.registry.names(), ["a", "b"])
        self.assertEqual(self.registry.names(), ["a", "b"])  # repeat

    def test_fresh_registry_empty(self):
        self.assertEqual(self.registry.names(), [])


# ============================================================
# 测试 20-21: get_macro_data
# ============================================================

class TestGetMacroData(unittest.TestCase):
    """测试 get_macro_data 完整流程。"""

    def setUp(self):
        self.raw_df = pd.DataFrame({
            "date": ["2024-01-15", "2024-02-15", "2024-03-15"],
            "value": [0.3, 0.7, 1.0],
        })

    def test_full_pipeline(self):
        provider = CallableMacroProvider(
            name="mock_provider",
            fetcher=lambda code, **kw: self.raw_df.copy(),
        )
        result = get_macro_data("cn_cpi_yoy", provider)
        self.assertEqual(result.attrs["code"], "CN_CPI_YOY")
        self.assertEqual(result.attrs["name"], "中国CPI同比")
        self.assertEqual(len(result), 3)
        self.assertEqual(list(result.columns), ["date", "value"])

    def test_with_date_filter(self):
        provider = CallableMacroProvider(
            name="mock_provider",
            fetcher=lambda code, **kw: self.raw_df.copy(),
        )
        result = get_macro_data(
            "CN_CPI_YOY", provider,
            start_date="2024-02-01", end_date="2024-02-28",
        )
        self.assertEqual(len(result), 1)

    def test_non_provider_raises_type_error(self):
        with self.assertRaises(TypeError):
            get_macro_data("CN_CPI_YOY", "not_a_provider")

    def test_invalid_code_raises_value_error(self):
        provider = CallableMacroProvider(
            name="mock", fetcher=lambda **kw: self.raw_df.copy()
        )
        with self.assertRaises(ValueError):
            get_macro_data("INVALID_CODE", provider)

    def test_provider_returns_bad_df_raises(self):
        """Provider 返回缺少 date 列的非法 DataFrame 时应报错。"""
        bad_df = pd.DataFrame({"wrong_column": [1, 2, 3]})
        provider = CallableMacroProvider(
            name="bad_provider",
            fetcher=lambda code, **kw: bad_df,
        )
        with self.assertRaises(ValueError):
            get_macro_data("CN_CPI_YOY", provider)


if __name__ == "__main__":
    unittest.main()
