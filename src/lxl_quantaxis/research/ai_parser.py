"""AI-powered investment thesis extraction.

Converts free-text research notes into structured InvestmentThesis
objects.  Uses LLM when available; falls back to a rule-based parser
when LLM is unavailable.

Safety: AI output is validated through a strict schema before use.
No code execution.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from src.lxl_quantaxis.core.logging import get_logger
from src.lxl_quantaxis.research.thesis import InvestmentThesis

_log = get_logger("research.ai_parser")

# ── Maximum input length (guardrail) ──
MAX_INPUT_LENGTH = 8000

# ── Schema for validation ──
ALLOWED_STYLES = frozenset({"value", "growth", "momentum", "event_driven",
                             "macro", "sector_rotation", "quantitative",
                             "unknown"})
ALLOWED_HORIZONS = frozenset({"short", "medium", "long", "unknown"})
ALLOWED_CONVICTIONS = frozenset({"low", "medium", "high", "unknown"})


@dataclass
class ParsedThesis:
    """Structured extraction result."""
    symbol: str = ""
    title: str = ""
    core_argument: str = ""
    bullish_reasons: str = ""
    bearish_reasons: str = ""
    key_risks: str = ""
    investment_style: str = "unknown"
    time_horizon: str = "unknown"
    conviction: str = "unknown"
    related_factors: str = ""
    confidence: float = 0.0
    source: str = "rule"  # "llm" or "rule"

    def to_thesis(self) -> InvestmentThesis:
        return InvestmentThesis(
            symbol=self.symbol,
            title=self.title,
            core_argument=self.core_argument,
            bullish_reasons=self.bullish_reasons,
            bearish_reasons=self.bearish_reasons,
            key_risks=self.key_risks,
            conviction=self.conviction,
            time_horizon=self.time_horizon,
            tags=f"ai-parsed,style-{self.investment_style},source-{self.source}",
        )


# ═══════════════════════════════════════════════════════════
# Rule-based fallback parser
# ═══════════════════════════════════════════════════════════

_BULL_KEYWORDS = ["看好", "利多", "利好", "买入", "增持", "看多", "bull",
                   "上升", "增长", "提升", "扩张", "加速", "超预期"]
_BEAR_KEYWORDS = ["看空", "利空", "卖出", "减持", "bear", "下跌", "下降",
                   "衰退", "萎缩", "减速", "低于预期", "风险"]
_RISK_KEYWORDS = ["风险", "注意", "警惕", "谨慎", "不确定性", "波动"]

_STYLE_PATTERNS = {
    "value": ["低估值", "价值", "便宜", "被低估", "value", "PE低", "PB低"],
    "growth": ["成长", "增长", "growth", "高增长", "扩张"],
    "momentum": ["趋势", "动量", "momentum", "突破", "新高"],
    "macro": ["宏观", "利率", "通胀", "政策", "央行", "GDP"],
    "sector_rotation": ["板块", "行业", "轮动", "产业链"],
    "event_driven": ["事件", "公告", "财报", "重组", "收购"],
}


def _rule_based_parse(text: str) -> ParsedThesis:
    """Extract thesis structure using keyword heuristics.

    This is a deterministic fallback. It does NOT use AI/LLM.
    """
    result = ParsedThesis()

    # Symbol detection: 6-digit numeric or common patterns
    sym_match = re.search(r'\b([36]0\d{4}|00\d{4}|68\d{4})\b', text)
    if sym_match:
        result.symbol = sym_match.group(1)

    # Title: first sentence up to 80 chars
    sentences = re.split(r'[。！？\n]', text)
    result.title = (sentences[0].strip()[:80] if sentences else
                    text.strip()[:80])

    # Core argument: first substantive paragraph
    for s in sentences[1:5] if len(sentences) > 1 else [text]:
        s = s.strip()
        if len(s) > 5:
            result.core_argument = s[:200]
            break

    # Bullish reasons
    bull_parts = []
    for line in text.split("\n"):
        if any(kw in line for kw in _BULL_KEYWORDS):
            bull_parts.append(line.strip()[:120])
    result.bullish_reasons = "; ".join(bull_parts[:5]) if bull_parts else "未提取到看多理由"

    # Bearish reasons
    bear_parts = []
    for line in text.split("\n"):
        if any(kw in line for kw in _BEAR_KEYWORDS):
            bear_parts.append(line.strip()[:120])
    result.bearish_reasons = "; ".join(bear_parts[:5]) if bear_parts else "未提取到看空理由"

    # Risks
    risk_parts = []
    for line in text.split("\n"):
        if any(kw in line for kw in _RISK_KEYWORDS):
            risk_parts.append(line.strip()[:120])
    result.key_risks = "; ".join(risk_parts[:5]) if risk_parts else "未提取到风险提示"

    # Investment style
    for style, keywords in _STYLE_PATTERNS.items():
        if any(kw in text for kw in keywords):
            result.investment_style = style
            break

    # Time horizon heuristics
    lower = text.lower()
    if any(w in lower for w in ["短期", "短线", "周", "日内"]):
        result.time_horizon = "short"
    elif any(w in lower for w in ["长期", "数年", "年"]):
        result.time_horizon = "long"
    else:
        result.time_horizon = "medium"

    result.confidence = 0.3  # rule-based has lower confidence
    result.source = "rule"

    return _validate(result)


# ═══════════════════════════════════════════════════════════
# LLM-based parser
# ═══════════════════════════════════════════════════════════

_EXTRACTION_PROMPT = """You are an investment research analyst. Extract structured investment thesis from the text below.

Return ONLY a JSON object with these fields:
{
  "symbol": "stock code if mentioned, else empty string",
  "title": "brief summary (max 80 chars)",
  "core_argument": "the main investment argument",
  "bullish_reasons": "key bullish points",
  "bearish_reasons": "key bearish points or counter-arguments",
  "key_risks": "identified risks",
  "investment_style": "value|growth|momentum|event_driven|macro|sector_rotation|quantitative|unknown",
  "time_horizon": "short|medium|long|unknown",
  "conviction": "low|medium|high|unknown"
}

Rules:
- Extract facts from the text only. Do not invent.
- If a field has no information, use empty string.
- Do not include any text outside the JSON.

Text:
{text}"""


def _llm_parse(text: str) -> ParsedThesis:
    """Use LLM to extract structured thesis. Falls back to rule-based on failure."""
    try:
        from src.ai.engine import LLMClient

        client = LLMClient()
        if not client.api_key:
            _log.info("LLM not configured, using rule-based parser")
            return _rule_based_parse(text)

        prompt = _EXTRACTION_PROMPT.format(text=text[:MAX_INPUT_LENGTH])
        response = client.ask(prompt, temperature=0.1)

        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            _log.warning("LLM response contained no JSON, falling back to rule-based")
            return _rule_based_parse(text)

        data = json.loads(json_match.group(0))

        result = ParsedThesis(
            symbol=str(data.get("symbol", "")).strip()[:20],
            title=str(data.get("title", ""))[:80],
            core_argument=str(data.get("core_argument", ""))[:500],
            bullish_reasons=str(data.get("bullish_reasons", ""))[:500],
            bearish_reasons=str(data.get("bearish_reasons", ""))[:500],
            key_risks=str(data.get("key_risks", ""))[:500],
            investment_style=str(data.get("investment_style", "unknown")),
            time_horizon=str(data.get("time_horizon", "unknown")),
            conviction=str(data.get("conviction", "unknown")),
            confidence=0.75,
            source="llm",
        )
        return _validate(result)

    except Exception as e:
        _log.warning(f"LLM parsing failed: {e}, falling back to rule-based")
        return _rule_based_parse(text)


# ═══════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════

def _validate(result: ParsedThesis) -> ParsedThesis:
    """Validate and sanitize parsed thesis output."""
    # Clamp fields to allowed values
    if result.investment_style not in ALLOWED_STYLES:
        result.investment_style = "unknown"
    if result.time_horizon not in ALLOWED_HORIZONS:
        result.time_horizon = "unknown"
    if result.conviction not in ALLOWED_CONVICTIONS:
        result.conviction = "unknown"

    # Confidence must be in [0, 1]
    result.confidence = max(0.0, min(1.0, result.confidence))

    # Source must be "llm" or "rule"
    if result.source not in ("llm", "rule"):
        result.source = "rule"

    return result


# ═══════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════

def parse_thesis(text: str, use_llm: bool = True) -> ParsedThesis:
    """Parse natural language investment text into structured thesis.

    Args:
        text: Free-text investment research note
        use_llm: Try LLM first (falls back to rule-based on failure)

    Returns:
        ParsedThesis with structured fields and confidence score
    """
    if not text or not text.strip():
        return ParsedThesis(confidence=0.0, source="rule")

    text = text.strip()[:MAX_INPUT_LENGTH]

    if use_llm:
        return _llm_parse(text)

    return _rule_based_parse(text)


def parse_and_save(text: str, use_llm: bool = True) -> int:
    """Parse text AND save the result as a ResearchNote. Returns note ID."""
    parsed = parse_thesis(text, use_llm=use_llm)
    thesis = parsed.to_thesis()
    return thesis.save()
