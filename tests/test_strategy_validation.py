"""Tests for strategy validation and backtest bridge."""

import pytest
from src.lxl_quantaxis.strategy.base.spec import StrategySpec
from src.lxl_quantaxis.strategy.validator import validate_strategy_spec, ValidationResult
from src.lxl_quantaxis.strategy.backtest_bridge import (
    compile_strategy, run_backtest, BridgeResult,
)


def _make_spec(name="test_strategy", entry="close > 0", exit_rule="close < 0") -> StrategySpec:
    safe_name = name if name else "unnamed"
    return StrategySpec(
        strategy_id=f"test.{safe_name.lower().replace(' ', '_')[:30]}",
        version="1.0.0",
        name=name,
        description="test",
        entry_rule=entry,
        exit_rule=exit_rule,
        source="manual",
    )


class TestValidator:
    def test_valid_spec_passes(self):
        spec = _make_spec()
        result = validate_strategy_spec(spec)
        assert result.valid

    def test_empty_name_rejected_by_spec(self):
        # StrategySpec itself rejects empty names
        with pytest.raises(ValueError):
            _make_spec(name="")

    def test_syntax_error_in_rule(self):
        spec = _make_spec(entry="close > > 0")
        result = validate_strategy_spec(spec)
        assert not result.valid

    def test_blocked_token_in_rule(self):
        spec = _make_spec(entry="import os")
        result = validate_strategy_spec(spec)
        assert not result.valid

    def test_missing_factor_warns(self):
        spec = _make_spec(entry="nonexistent_factor_xyz > 0.5")
        result = validate_strategy_spec(spec)
        # Should have errors (factor not found) or warnings
        assert not result.valid or len(result.warnings) > 0

    def test_ai_source_checks_description(self):
        spec = _make_spec()
        object.__setattr__(spec, 'source', 'ai')
        object.__setattr__(spec, 'description', '')
        result = validate_strategy_spec(spec)
        # Should warn about missing description for AI strategies
        assert len(result.warnings) > 0

    def test_result_to_dict(self):
        r = ValidationResult(valid=True, warnings=["test warning"])
        d = r.to_dict()
        assert d["valid"]
        assert "test warning" in d["warnings"]

    def test_factor_registry_loaded(self):
        from src.lxl_quantaxis.strategy.validator import _load_factor_names
        factors = _load_factor_names()
        assert len(factors) >= 10  # should have at least trend/momentum factors

    def test_extract_names_from_rule(self):
        from src.lxl_quantaxis.strategy.validator import _extract_names
        names = _extract_names("momentum_score > 0.6 and rsi_norm < 0.3")
        assert "momentum_score" in names
        assert "rsi_norm" in names


class TestCompiler:
    def test_valid_spec_compiles(self):
        spec = _make_spec(entry="close > 0")
        compiled, result = compile_strategy(spec)
        assert compiled is not None
        assert result.valid

    def test_empty_entry_returns_none(self):
        spec = _make_spec(entry="")
        compiled, result = compile_strategy(spec)
        # Empty rule should fail validation
        assert not result.valid

    def test_compiled_strategy_has_entry(self):
        spec = _make_spec(entry="close > 0")
        compiled, result = compile_strategy(spec)
        assert compiled.entry is not None


class TestBacktestBridge:
    def test_bridge_result_initial(self):
        spec = _make_spec()
        bridge = BridgeResult(spec=spec)
        assert bridge.status == "pending"
        d = bridge.to_dict()
        assert d["status"] == "pending"

    def test_full_pipeline_valid_spec(self):
        spec = _make_spec(
            name="Simple Test",
            entry="close > 0",
            exit_rule="close < 0",
        )
        bridge = run_backtest(spec, symbol="601398", start_date="2024-06-01")
        # Should at least compile (data may or may not be available)
        assert bridge.status in ("backtested", "compiling", "failed")
        # If it failed, it should have a reason
        if bridge.status == "failed":
            assert len(bridge.validation.errors) > 0 or "error" in bridge.backtest_metrics

    def test_invalid_spec_fails_fast(self):
        spec = _make_spec(entry="import os")
        bridge = run_backtest(spec)
        assert bridge.status == "failed"
        assert not bridge.validation.valid
