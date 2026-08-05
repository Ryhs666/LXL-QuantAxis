"""Tests for AI research demo pipeline."""

import pytest
from demo_ai_research import run_demo


class TestDemoPipeline:
    def test_run_with_rule_mode(self):
        result = run_demo(
            idea="growth momentum strategy for tech stocks",
            symbol="000001",
            use_llm=False,
        )
        assert result["input"]
        assert result["symbol"] == "000001"
        assert "stages" in result
        # Each stage should have either a result or an error
        for stage in ["thesis", "factor_model", "strategy", "backtest", "analysis", "report"]:
            assert stage in result["stages"], f"Missing stage: {stage}"

    def test_pipeline_stages_have_data(self):
        result = run_demo(
            idea="value investing with low volatility",
            symbol="000001",
            use_llm=False,
        )
        # All 6 stages present, at least one succeeded without error
        stages = result["stages"]
        assert len(stages) == 6
        success_count = sum(1 for s in stages.values() if "error" not in s)
        assert success_count >= 3  # thesis + factor + strategy always work rule-based

    def test_empty_idea_handled(self):
        result = run_demo(idea="", symbol="000001", use_llm=False)
        assert result["input"] == ""

    def test_result_structure(self):
        result = run_demo(
            idea="momentum strategy", symbol="000001", use_llm=False,
        )
        assert "timestamp" in result
        assert isinstance(result["stages"], dict)
