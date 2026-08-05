"""Tests for AI thesis extraction."""

import pytest
from src.lxl_quantaxis.research.ai_parser import (
    parse_thesis, parse_and_save, ParsedThesis,
    _rule_based_parse, _validate,
)


class TestRuleBasedParser:
    def test_extracts_symbol(self):
        result = _rule_based_parse("600519 茅台大涨")
        assert result.symbol == "600519"

    def test_extracts_title(self):
        result = _rule_based_parse("茅台分析。白酒板块看好。")
        assert "茅台" in result.title

    def test_bullish_keywords(self):
        text = "看好AI服务器。云厂商资本开支提升利好。"
        result = _rule_based_parse(text)
        assert result.bullish_reasons != "未提取到看多理由"

    def test_bearish_keywords(self):
        text = "看空地产。销售持续下跌。"
        result = _rule_based_parse(text)
        assert "下跌" in result.bearish_reasons

    def test_risk_keywords(self):
        text = "风险在于估值过高。注意政策变化。"
        result = _rule_based_parse(text)
        assert result.key_risks != "未提取到风险提示"

    def test_style_detection(self):
        result = _rule_based_parse("低估值价值投资机会")
        assert result.investment_style == "value"

    def test_time_horizon(self):
        result = _rule_based_parse("短期交易机会")
        assert result.time_horizon == "short"

    def test_confidence_is_low(self):
        result = _rule_based_parse("test")
        assert result.confidence <= 0.5
        assert result.source == "rule"


class TestParseThesis:
    def test_empty_input(self):
        result = parse_thesis("", use_llm=False)
        assert result.confidence == 0.0

    def test_whitespace_input(self):
        result = parse_thesis("   ", use_llm=False)
        assert result.confidence == 0.0

    def test_rule_fallback_is_deterministic(self):
        text = "600519 茅台分析。看好白酒消费升级。风险：政策打压。"
        r1 = parse_thesis(text, use_llm=False)
        r2 = parse_thesis(text, use_llm=False)
        assert r1.symbol == r2.symbol
        assert r1.title == r2.title

    def test_converts_to_thesis(self):
        text = "600519 茅台看多。估值偏低。风险可控。"
        result = parse_thesis(text, use_llm=False)
        thesis = result.to_thesis()
        assert thesis.symbol == "600519"
        assert thesis.title

    def test_large_input_truncated(self):
        big = "A" * 10000
        result = parse_thesis(big, use_llm=False)
        assert result.title  # doesn't crash

    def test_llm_flag_off_uses_rule(self):
        result = parse_thesis("test", use_llm=False)
        assert result.source == "rule"


class TestValidation:
    def test_invalid_style_clamped(self):
        p = ParsedThesis(investment_style="hack_attempt")
        v = _validate(p)
        assert v.investment_style == "unknown"

    def test_invalid_horizon_clamped(self):
        p = ParsedThesis(time_horizon="forever")
        v = _validate(p)
        assert v.time_horizon == "unknown"

    def test_confidence_clamped(self):
        p = ParsedThesis(confidence=999.0)
        v = _validate(p)
        assert v.confidence == 1.0

        p2 = ParsedThesis(confidence=-5.0)
        v2 = _validate(p2)
        assert v2.confidence == 0.0

    def test_invalid_source_clamped(self):
        p = ParsedThesis(source="random")
        v = _validate(p)
        assert v.source == "rule"


class TestParseAndSave:
    def test_saves_and_returns_id(self):
        text = "600519 茅台。看好。低估值。风险可控。"
        nid = parse_and_save(text, use_llm=False)
        assert nid > 0

        from src.lxl_quantaxis.research.notebook import get_note, delete_note
        note = get_note(nid)
        assert note is not None
        assert note.symbol == "600519"
        assert "ai-parsed" in note.tags
        delete_note(nid)
