"""Tests for IC Decay Auto-Action — automatic factor weight reduction"""

import pytest
from src.factors.composer import SignalComposer, Condition, SignalRule
from src.factors.definitions import FactorCalculator


class TestConditionDecay:
    def test_condition_has_decay_factor(self):
        cond = Condition(factor="rsi_norm", operator="lt", threshold=0.3)
        assert cond.decay_factor == 1.0

    def test_condition_custom_decay(self):
        cond = Condition(factor="rsi_norm", operator="lt", threshold=0.3, decay_factor=0.3)
        assert cond.decay_factor == 0.3


class TestSignalComposerDecay:
    def test_apply_decay(self):
        c = SignalComposer("test")
        c.add_condition("rsi_norm", "lt", 0.3, weight=2)
        c.add_condition("ma_deviation", "lt", -0.02, weight=1)
        c.apply_decay("rsi_norm", 0.3)
        decaying = c.get_decaying_factors()
        assert "rsi_norm" in decaying
        assert decaying["rsi_norm"] == 0.3

    def test_apply_decay_to_nonexistent_factor(self):
        c = SignalComposer("test")
        c.add_condition("rsi_norm", "lt", 0.3)
        c.apply_decay("nonexistent", 0.5)
        assert len(c.get_decaying_factors()) == 0

    def test_get_active_factors(self):
        c = SignalComposer("test")
        c.add_condition("rsi_norm", "lt", 0.3, weight=2)
        c.add_condition("ma_deviation", "lt", -0.02, weight=1)
        c.apply_decay("rsi_norm", 0.5)
        active = c.get_active_factors()
        assert "rsi_norm" in active  # decayed but not zero
        assert "ma_deviation" in active

    def test_disabled_factor_not_active(self):
        c = SignalComposer("test")
        c.add_condition("rsi_norm", "lt", 0.3)
        c.apply_decay("rsi_norm", 0.0)
        disabled = "rsi_norm" not in c.get_active_factors()
        assert disabled

    def test_get_decaying_factors_empty(self):
        c = SignalComposer("test")
        c.add_condition("rsi_norm", "lt", 0.3)
        assert len(c.get_decaying_factors()) == 0


class TestAutoReduceWeights:
    def test_no_decay_no_changes(self):
        c = SignalComposer("test")
        c.add_condition("rsi_norm", "lt", 0.3, weight=2)

        calc = FactorCalculator.__new__(FactorCalculator)
        calc._decay_status = {
            "rsi_norm": {"current_ic": 0.15, "decaying": False, "below_zero_streak": 0},
        }
        changes = calc.auto_reduce_weights(c)
        assert len(changes) == 0  # 正常, 不调整

    def test_decaying_factor_disabled(self):
        c = SignalComposer("test")
        c.add_condition("rsi_norm", "lt", 0.3, weight=2)

        calc = FactorCalculator.__new__(FactorCalculator)
        calc._decay_status = {
            "rsi_norm": {"current_ic": -0.05, "decaying": True, "below_zero_streak": 6},
        }
        changes = calc.auto_reduce_weights(c)
        assert len(changes) == 1
        assert changes["rsi_norm"]["new_decay"] == 0.0  # 完全禁用

    def test_warning_factor_reduced(self):
        c = SignalComposer("test")
        c.add_condition("ma_cross", "gt", 0.5, weight=1)

        calc = FactorCalculator.__new__(FactorCalculator)
        calc._decay_status = {
            "ma_cross": {"current_ic": -0.01, "decaying": False, "below_zero_streak": 3},
        }
        changes = calc.auto_reduce_weights(c)
        assert len(changes) == 1
        assert changes["ma_cross"]["new_decay"] == 0.3  # 严重降权

    def test_weak_factor_reduced(self):
        c = SignalComposer("test")
        c.add_condition("test_factor", "lt", 0.5, weight=1)

        calc = FactorCalculator.__new__(FactorCalculator)
        calc._decay_status = {
            "test_factor": {"current_ic": 0.005, "decaying": False, "below_zero_streak": 0},
        }
        changes = calc.auto_reduce_weights(c)
        assert len(changes) == 1
        assert changes["test_factor"]["new_decay"] == 0.5  # 轻度降权
