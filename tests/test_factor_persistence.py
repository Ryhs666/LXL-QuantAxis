"""Tests for FactorPersistence — AI-mined factor disk persistence"""

import os
import json
import pytest
from src.ai.factor_persistence import FactorPersistence, factor_persistence


class TestFactorPersistence:
    def test_save_and_load_factor(self):
        fp = FactorPersistence()
        factor_def = {
            "name": "test_save_factor",
            "chinese_name": "测试因子",
            "category": "momentum",
            "logic": "Test momentum factor from AI",
            "python_code": "def calc_factor(data):\n    return data['close'].pct_change(5)",
        }
        path = fp.save_factor(factor_def, source_symbol="601398")
        assert path
        assert os.path.exists(path)

        loaded = fp.load_factor("test_save_factor")
        assert loaded is not None
        assert loaded["name"] == "test_save_factor"
        assert loaded["category"] == "momentum"

        # cleanup
        fp.delete_factor("test_save_factor")

    def test_load_all_factors(self):
        fp = FactorPersistence()
        factors = fp.load_all_factors()
        assert isinstance(factors, list)

    def test_list_factors(self):
        fp = FactorPersistence()
        names = fp.list_factors()
        assert isinstance(names, list)

    def test_update_performance(self):
        fp = FactorPersistence()
        fp.save_factor({
            "name": "test_perf_factor",
            "chinese_name": "性能测试",
            "category": "trend",
            "logic": "Test",
            "python_code": "def calc_factor(data):\n    return data['close']",
        })
        fp.update_performance("test_perf_factor", {
            "signals_generated": 10,
            "win_rate": 0.65,
            "decaying": False,
        })
        loaded = fp.load_factor("test_perf_factor")
        assert loaded["performance"]["signals_generated"] == 10
        assert loaded["performance"]["win_rate"] == 0.65

        fp.delete_factor("test_perf_factor")

    def test_delete_factor(self):
        fp = FactorPersistence()
        fp.save_factor({
            "name": "test_delete_me",
            "chinese_name": "待删除",
            "category": "test",
            "logic": "Delete test",
            "python_code": "def calc_factor(data):\n    return data['close']",
        })
        assert fp.delete_factor("test_delete_me")
        assert not fp.delete_factor("nonexistent")

    def test_global_singleton(self):
        assert factor_persistence is not None

    def test_safe_code_passes(self):
        assert FactorPersistence.is_safe_code("def calc_factor(data):\n    return data['close'].shift(1)")

    def test_unsafe_code_blocked(self):
        assert not FactorPersistence.is_safe_code("import os; os.system('rm -rf /')")
        assert not FactorPersistence.is_safe_code("eval('1+1')")
        assert not FactorPersistence.is_safe_code("__import__('os')")


class TestFactorPersistenceReload:
    def test_reload_returns_int(self):
        fp = FactorPersistence()
        count = fp.reload_into_registry(verbose=False)
        assert isinstance(count, int)
        assert count >= 0
