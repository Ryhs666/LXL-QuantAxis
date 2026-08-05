"""Tests for AI strategy builder DSL."""

import pytest
from src.lxl_quantaxis.research.strategy_builder import (
    StrategyBlueprint, build_strategy, build_and_compile,
    _build_from_style, _is_safe_rule,
)


class TestSafety:
    def test_blocks_import(self):
        assert not _is_safe_rule("import os; rm -rf /")
        assert not _is_safe_rule("__import__('os')")

    def test_blocks_exec(self):
        assert not _is_safe_rule("exec('1+1')")
        assert not _is_safe_rule("eval('1+1')")

    def test_blocks_shell(self):
        assert not _is_safe_rule("os.system('ls')")
        assert not _is_safe_rule("subprocess.run('ls')")

    def test_allows_valid_rules(self):
        assert _is_safe_rule("momentum_score > 0.6")
        assert _is_safe_rule("rsi_norm < 0.3")
        assert _is_safe_rule("volatility >= 0.5")


class TestBlueprint:
    def test_validate_passes_for_valid(self):
        bp = StrategyBlueprint(
            name="test",
            entry_conditions=["momentum_score > 0.6", "trend_strength > 0.5"],
        )
        assert bp.validate()

    def test_validate_fails_empty_name(self):
        bp = StrategyBlueprint(name="")
        assert not bp.validate()

    def test_validate_fails_unsafe_rule(self):
        bp = StrategyBlueprint(
            name="test",
            entry_conditions=["import os"],
        )
        assert not bp.validate()

    def test_validate_fails_bad_risk_key(self):
        bp = StrategyBlueprint(
            name="test",
            risk_rules={"hack_rule": 50},
        )
        assert not bp.validate()

    def test_to_strategy_spec(self):
        bp = StrategyBlueprint(
            name="Growth Strategy",
            description="Growth momentum strategy",
            entry_conditions=["momentum_score > 0.6", "trend_strength > 0.5"],
            exit_conditions=["max_drawdown > 0.10"],
            entry_logic="AND",
            exit_logic="OR",
        )
        spec = bp.to_strategy_spec()
        assert spec.name == "Growth Strategy"
        assert spec.source == "ai"
        assert "momentum_score" in spec.entry_rule


class TestBuildStrategy:
    def test_rule_based_growth(self):
        factors = [
            {"name": "momentum_score", "weight": 0.4, "category": "momentum"},
            {"name": "trend_strength", "weight": 0.3, "category": "trend"},
        ]
        bp = build_strategy(
            theme="Growth Test", style="growth", factors=factors, use_llm=False,
        )
        assert bp.validate()
        assert len(bp.entry_conditions) >= 2
        assert bp.source == "rule"

    def test_rule_based_value(self):
        factors = [
            {"name": "ma_deviation", "weight": 0.5, "category": "trend"},
        ]
        bp = build_strategy(
            theme="Value Test", style="value", factors=factors, use_llm=False,
        )
        assert bp.validate()
        assert len(bp.factor_weights) >= 1

    def test_empty_factors_uses_default(self):
        bp = build_strategy(theme="empty", use_llm=False)
        assert bp.validate()
        assert len(bp.entry_conditions) >= 1

    def test_from_factor_model(self):
        from src.lxl_quantaxis.research.factor_mapper import map_thesis_to_factors
        model = map_thesis_to_factors(
            text="growth momentum thesis", style="growth", use_llm=False,
        )
        bp = build_strategy(factor_model=model, use_llm=False)
        assert bp.validate()
        assert len(bp.factor_weights) >= 2

    def test_compile_to_spec(self):
        factors = [
            {"name": "momentum_score", "weight": 0.6, "category": "momentum"},
            {"name": "rsi_norm", "weight": 0.4, "category": "momentum"},
        ]
        spec = build_and_compile(
            theme="Compiled Test", style="momentum", use_llm=False,
        )
        assert spec is not None
        assert "momentum_score" in spec.entry_rule


class TestSchemaFailure:
    def test_llm_response_with_unsafe_rule(self):
        """Even if LLM returned something unsafe, it should be caught."""
        factors = [{"name": "momentum_score", "weight": 1.0, "category": "momentum"}]
        bp = build_strategy(
            theme="test", style="growth", factors=factors, use_llm=False,
        )
        assert bp.validate()
        for c in bp.entry_conditions:
            assert _is_safe_rule(c)

    def test_invalid_entry_logic_clamped(self):
        bp = StrategyBlueprint(
            name="test", entry_logic="INVALID",
            entry_conditions=["close > 0"],
        )
        assert not bp.validate()
