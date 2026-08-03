"""Versioned factor registry, pipeline, validation, and legacy equivalence."""

import unittest

import numpy as np
import pandas as pd

from src.factors.definitions import FactorCalculator, get_v2_factor_registry
from src.factors.fundamental import get_v2_fundamental_registry
from src.lxl_quantaxis.factor import (
    FactorCategory,
    FactorPipeline,
    FactorRegistry,
    FactorSpec,
    FactorValidator,
    LegacyFactorAdapter,
)


class FactorRegistryTests(unittest.TestCase):
    def test_specs_are_versioned_and_duplicate_versions_are_rejected(self) -> None:
        spec = FactorSpec(
            factor_id="momentum.rsi",
            version="1.0.0",
            category=FactorCategory.MOMENTUM,
            description="RSI",
            lookback=14,
            availability_lag=1,
        )
        registry = FactorRegistry().register(spec)

        self.assertEqual(registry.get("momentum.rsi", "1.0.0"), spec)
        with self.assertRaises(ValueError):
            registry.register(spec)


class FactorPipelineTests(unittest.TestCase):
    def test_availability_lag_prevents_current_row_from_using_future_values(self) -> None:
        values = pd.DataFrame([[1.0, 2.0], [3.0, 4.0], [100.0, -100.0]], columns=["A", "B"])
        pipeline = FactorPipeline(availability_lag=1, winsor_limits=(0.0, 1.0), standardize=True)

        original = pipeline.transform(values)
        changed = values.copy()
        changed.iloc[-1] = [9999.0, -9999.0]

        pd.testing.assert_frame_equal(original, pipeline.transform(changed))
        self.assertTrue(original.iloc[0].isna().all())

    def test_pipeline_is_deterministic_and_neutralizes_groups(self) -> None:
        values = pd.DataFrame([[1.0, 3.0, 10.0, 14.0]], columns=["A", "B", "C", "D"])
        groups = pd.Series({"A": "bank", "B": "bank", "C": "tech", "D": "tech"})
        pipeline = FactorPipeline(availability_lag=0, neutralize_groups=groups, standardize=False)

        first = pipeline.transform(values)
        second = pipeline.transform(values)

        pd.testing.assert_frame_equal(first, second)
        self.assertAlmostEqual(float(first[["A", "B"]].mean(axis=1).iloc[0]), 0.0)
        self.assertAlmostEqual(float(first[["C", "D"]].mean(axis=1).iloc[0]), 0.0)


class FactorValidationTests(unittest.TestCase):
    def test_synthetic_cross_section_has_positive_ic_and_rank_ic(self) -> None:
        rng = np.random.default_rng(7)
        index = pd.date_range("2026-01-01", periods=40)
        columns = [f"S{i}" for i in range(20)]
        factor = pd.DataFrame(rng.normal(size=(40, 20)), index=index, columns=columns)
        forward_returns = factor * 0.05 + pd.DataFrame(
            rng.normal(scale=0.005, size=(40, 20)), index=index, columns=columns
        )

        report = FactorValidator().validate(factor, forward_returns)

        self.assertGreater(report.ic_mean, 0.9)
        self.assertGreater(report.rank_ic_mean, 0.9)
        self.assertGreater(report.stability, 0.9)


class LegacyFactorAdapterTests(unittest.TestCase):
    def test_legacy_rsi_matches_existing_calculator(self) -> None:
        close = pd.Series(np.linspace(10.0, 30.0, 80))
        data = pd.DataFrame(
            {
                "date": pd.date_range("2026-01-01", periods=80),
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": 1000,
            }
        )
        expected = FactorCalculator(data).f_rsi()

        actual = LegacyFactorAdapter().compute("rsi_norm", data)

        pd.testing.assert_series_equal(actual, expected, check_names=False)
        self.assertIsNotNone(get_v2_factor_registry().get("legacy.rsi_norm", "1.0.0"))
        self.assertEqual(get_v2_fundamental_registry().get("fundamental.pe").category, FactorCategory.VALUE)


if __name__ == "__main__":
    unittest.main()
