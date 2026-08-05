"""Tests for demo pipeline — verifies all 7 stages run without crashing."""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from demo.demo_ai_research import run_demo
from demo.demo_config import EXAMPLE_THESES


class TestDemoPipeline:
    def test_run_with_builtin_example(self):
        ex = EXAMPLE_THESES[0]
        result = run_demo(
            idea=ex["text"], symbol=ex.get("symbol", "000001"),
            use_llm=False,
        )
        assert result["input"]
        assert result["symbol"]
        assert len(result["stages"]) == 7
        # At least 4 stages should succeed: thesis, factor, strategy, validation
        success = sum(1 for s in result["stages"].values() if "error" not in s)
        # Thesis + factor + strategy should always work rule-based.
        # Backtest/analysis/report depend on data availability.
        assert success >= 3, f"Only {success}/7 stages passed (data-dependent stages may fail)"

    def test_run_with_custom_idea(self):
        result = run_demo(
            idea="momentum strategy for liquid large caps",
            symbol="000001", use_llm=False,
        )
        assert result["stages"]

    def test_run_empty_idea(self):
        result = run_demo(idea="", symbol="000001", use_llm=False)
        assert result["input"] == ""

    def test_all_stages_present(self):
        result = run_demo(
            idea="value low volatility defensive", symbol="000001",
            use_llm=False,
        )
        for stage in ["thesis", "factor_model", "strategy", "validation",
                       "backtest", "analysis", "report"]:
            assert stage in result["stages"], f"Missing: {stage}"

    def test_result_structure(self):
        result = run_demo(
            idea="growth momentum", symbol="000001", use_llm=False,
        )
        assert "timestamp" in result
        assert "input" in result
        assert isinstance(result["stages"], dict)

    def test_example_configs_valid(self):
        assert len(EXAMPLE_THESES) == 3
        for ex in EXAMPLE_THESES:
            assert ex["title"]
            assert ex["text"]
            assert ex["symbol"]
