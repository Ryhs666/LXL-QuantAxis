"""Tests for research report generator."""

import os
import tempfile
import pytest
from src.lxl_quantaxis.research.report_generator import (
    ResearchReport, generate_report, _safe_get, _format_metric,
)


class TestResearchReport:
    def test_empty_report_renders(self):
        r = ResearchReport(title="Test", date="2026-01-01")
        md = r.to_markdown()
        assert "Test" in md
        assert "1. 投资摘要" in md

    def test_html_renders(self):
        r = ResearchReport(title="Test")
        html = r.to_html()
        assert "<h1>" in html
        assert "Test" in html

    def test_save_markdown(self):
        r = ResearchReport(title="Test Save")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test.md")
            r.save_markdown(path)
            assert os.path.exists(path)
            with open(path, encoding="utf-8") as f:
                assert "Test Save" in f.read()

    def test_save_html(self):
        r = ResearchReport(title="Test HTML")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test.html")
            r.save_html(path)
            assert os.path.exists(path)

    def test_save_both(self):
        r = ResearchReport(title="Test Both")
        with tempfile.TemporaryDirectory() as d:
            paths = r.save(d)
            assert os.path.exists(paths["markdown"])
            assert os.path.exists(paths["html"])


class TestGenerateReport:
    def test_minimal_input(self):
        r = generate_report(symbol="600519")
        assert r.symbol == "600519"
        assert r.title
        assert r.investment_summary

    def test_with_thesis(self):
        from src.lxl_quantaxis.research.thesis import InvestmentThesis
        thesis = InvestmentThesis(
            symbol="600519", title="Moutai Bull",
            core_argument="consumption upgrade thesis",
            bullish_reasons="price hike", bearish_reasons="policy risk",
        )
        r = generate_report(symbol="600519", thesis=thesis)
        # core_argument → investment_summary; bullish → thesis section
        assert "consumption" in r.investment_summary.lower()
        assert "price hike" in r.thesis

    def test_with_backtest_metrics(self):
        metrics = {"夏普比率": "1.50", "总收益率": "+25%", "胜率": "60%", "最大回撤": "-10%"}
        r = generate_report(symbol="000001", backtest_metrics=metrics)
        assert "1.50" in r.backtest_analysis
        assert "-10" in r.backtest_analysis

    def test_with_backtest_assessment(self):
        from src.lxl_quantaxis.ai.backtest_analyzer import _rule_analyze
        metrics = {"夏普比率": 2.0, "总收益率": "+35%", "胜率": "65%",
                   "最大回撤": "-8%", "交易次数": "25"}
        assessment = _rule_analyze(metrics)
        r = generate_report(symbol="000001", backtest_metrics=metrics,
                           backtest_assessment=assessment)
        assert r.backtest_analysis
        assert r.conclusion

    def test_with_factor_model(self):
        from src.lxl_quantaxis.research.factor_mapper import map_thesis_to_factors
        model = map_thesis_to_factors(
            text="growth thesis", style="growth", use_llm=False,
        )
        r = generate_report(symbol="600519", factor_model=model)
        assert r.factor_analysis
        assert "权重" in r.factor_analysis

    def test_with_portfolio_assessment(self):
        from src.lxl_quantaxis.portfolio.intelligence import assess_portfolio
        strategies = [
            {"name": "growth", "expected_return": 15, "risk": 18, "sharpe": 1.2,
             "max_drawdown": -15, "factor_exposure": {"momentum_score": 0.5}},
        ]
        pa = assess_portfolio(strategies)
        r = generate_report(symbol="000001", portfolio_assessment=pa)
        assert r.portfolio_analysis
        assert r.risk_section

    def test_full_pipeline(self):
        """End-to-end: thesis → factors → backtest → report."""
        from src.lxl_quantaxis.research.thesis import InvestmentThesis
        from src.lxl_quantaxis.research.factor_mapper import map_thesis_to_factors
        from src.lxl_quantaxis.ai.backtest_analyzer import _rule_analyze

        thesis = InvestmentThesis(
            symbol="600519", core_argument="consumption upgrade",
            bullish_reasons="direct sales growth", bearish_reasons="policy risk",
        )
        model = map_thesis_to_factors(thesis=thesis, use_llm=False)
        metrics = {"夏普比率": 1.8, "总收益率": "+30%", "胜率": "62%",
                   "最大回撤": "-9%"}
        assessment = _rule_analyze(metrics)

        r = generate_report(
            symbol="600519", thesis=thesis, factor_model=model,
            backtest_metrics=metrics, backtest_assessment=assessment,
        )
        md = r.to_markdown()
        assert "600519" in md
        assert "consumption" in md.lower()
        assert "1.8" in md

    def test_missing_data_generates_placeholder(self):
        r = generate_report(symbol="000001")
        assert "暂无" in r.factor_analysis or "暂无" in r.backtest_analysis

    def test_format_metric(self):
        assert "1.50" in _format_metric(1.5)
        assert "25.00" in _format_metric("+25%")

    def test_safe_get_with_none(self):
        assert _safe_get(None, "x") == ""
        assert _safe_get({"a": 1}, "b") == ""
        assert _safe_get({"a": 1}, "a") == "1"
