"""Tests for AI backtest analyst."""

import pytest
from src.lxl_quantaxis.ai.backtest_analyzer import (
    BacktestAssessment, analyze_backtest, analyze_and_log,
    _rule_analyze, _parse_metric,
)


class TestParseMetric:
    def test_float(self):
        assert _parse_metric({"a": 1.5}, "a") == 1.5

    def test_string_percent(self):
        assert _parse_metric({"a": "+15.3%"}, "a") == 15.3

    def test_string_negative(self):
        assert _parse_metric({"a": "-25.0%"}, "a") == -25.0

    def test_missing_key(self):
        assert _parse_metric({}, "x") == 0.0


class TestRuleAnalyze:
    def test_excellent_strategy(self):
        metrics = {"夏普比率": 2.0, "总收益率": "+35%", "胜率": "65%",
                   "最大回撤": "-8%", "交易次数": "25"}
        a = _rule_analyze(metrics)
        assert "优秀" in a.summary or "可行" in a.summary
        assert len(a.strengths) >= 1
        assert a.source == "rule"

    def test_poor_strategy(self):
        metrics = {"夏普比率": -0.5, "总收益率": "-10%", "胜率": "35%",
                   "最大回撤": "-30%", "交易次数": "5"}
        a = _rule_analyze(metrics)
        assert "无效" in a.summary or "边际" in a.summary
        assert len(a.weaknesses) >= 1
        assert a.risk_warning

    def test_high_return_high_risk(self):
        metrics = {"夏普比率": 0.8, "总收益率": "+50%", "胜率": "50%",
                   "最大回撤": "-25%", "交易次数": "15"}
        a = _rule_analyze(metrics)
        # Sharpe 0.8 → viable, not excellent. Risk warning should fire due to -25% drawdown.
        assert a.summary
        assert len(a.risk_warning) > 0  # drawdown > 15% triggers warning
        assert any("drawdown" in s.lower() or "回撤" in s or "止损" in s
                   for s in a.optimization_suggestions)

    def test_empty_metrics_gets_all_fields(self):
        a = _rule_analyze({})
        assert a.summary
        assert a.strengths
        assert a.weaknesses
        assert a.risk_warning

    def test_confidence_for_rule(self):
        a = _rule_analyze({"夏普比率": 0.5})
        assert 0 < a.confidence < 0.5  # rule-based has lower confidence


class TestAnalyzeBacktest:
    def test_rule_mode(self):
        a = analyze_backtest({"夏普比率": 1.0}, "test", use_llm=False)
        assert a.source == "rule"
        assert a.summary

    def test_empty_metrics(self):
        a = analyze_backtest({})
        assert a.confidence == 0.0

    def test_to_dict(self):
        a = _rule_analyze({"夏普比率": 1.5})
        d = a.to_dict()
        assert "summary" in d
        assert isinstance(d["strengths"], list)

    def test_analyze_and_log(self):
        a = analyze_and_log(
            {"夏普比率": 0.8, "总收益率": "+12%"},
            strategy_name="test_strategy",
            use_llm=False,
        )
        assert a.summary
        assert a.source == "rule"

    def test_optimization_suggestions_present(self):
        a = _rule_analyze({"夏普比率": 0.3, "最大回撤": "-18%", "胜率": "40%",
                           "交易次数": "8"})
        assert len(a.optimization_suggestions) >= 1
