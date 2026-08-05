"""AI Factor Mapper — InvestmentThesis → quant factor model.

Maps structured investment theses to concrete factors from the
existing FACTOR_REGISTRY.  Reuses, never duplicates.

Safety: LLM output schema-validated. No code execution.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from src.lxl_quantaxis.core.logging import get_logger

_log = get_logger("research.factor_mapper")

# ── Load available factor names at import time ──
_AVAILABLE_FACTORS: dict[str, str] = {}  # name → category


def _load_factors() -> dict[str, str]:
    global _AVAILABLE_FACTORS
    if not _AVAILABLE_FACTORS:
        try:
            from src.factors.definitions import FACTOR_REGISTRY
            _AVAILABLE_FACTORS = {n: f.category for n, f in FACTOR_REGISTRY.items()}
        except ImportError:
            _AVAILABLE_FACTORS = {}
    return _AVAILABLE_FACTORS


# ═══════════════════════════════════════════════════════════
# Data model
# ═══════════════════════════════════════════════════════════

@dataclass
class FactorWeight:
    name: str = ""
    weight: float = 0.0
    reason: str = ""
    category: str = ""


@dataclass
class FactorModel:
    theme: str = ""
    factors: list[FactorWeight] = field(default_factory=list)
    rationale: str = ""
    confidence: float = 0.0
    source: str = "rule"

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "factors": [
                {"name": f.name, "weight": f.weight, "reason": f.reason,
                 "category": f.category}
                for f in self.factors
            ],
            "rationale": self.rationale,
            "confidence": self.confidence,
            "source": self.source,
        }

    def validate(self) -> bool:
        """Check all factor names exist in registry."""
        registry = _load_factors()
        for f in self.factors:
            if f.name not in registry:
                return False
        total = sum(f.weight for f in self.factors)
        if not (0.99 < total < 1.01):
            return False
        return True


# ═══════════════════════════════════════════════════════════
# Style → factor category mapping (rule-based)
# ═══════════════════════════════════════════════════════════

_STYLE_FACTOR_MAP: dict[str, list[tuple[str, float, str]]] = {
    "value": [
        ("ma_deviation", 0.35, "价格偏离均线=低估信号"),
        ("bollinger_pos", 0.25, "布林下轨=廉价区域"),
        ("volatility", 0.20, "低波动=防御性"),
        ("volume_ratio", 0.20, "缩量=恐慌出清"),
    ],
    "growth": [
        ("momentum_score", 0.30, "多周期动量=持续增长"),
        ("trend_strength", 0.25, "趋势强度=增长确认"),
        ("roc_10", 0.25, "短期变化率=增长动能"),
        ("volume_trend", 0.20, "量价配合=健康增长"),
    ],
    "momentum": [
        ("momentum_score", 0.35, "多周期动量=趋势持续"),
        ("roc_10", 0.25, "价格变化率=突破强度"),
        ("rsi_norm", 0.25, "RSI=超买动力"),
        ("volume_ratio", 0.15, "放量=动量确认"),
    ],
    "event_driven": [
        ("volume_ratio", 0.40, "异动量=事件驱动"),
        ("rsi_norm", 0.30, "RSI极值=事件冲击"),
        ("atr_ratio", 0.30, "ATR扩大=波动加剧"),
    ],
    "macro": [
        ("trend_strength", 0.35, "趋势=宏观方向"),
        ("bollinger_width", 0.25, "布林宽度=波动预期"),
        ("volatility", 0.25, "波动率=市场情绪"),
        ("ma_slope", 0.15, "均线斜率=宏观拐点"),
    ],
    "sector_rotation": [
        ("price_position", 0.35, "价格位置=板块轮动"),
        ("volume_trend", 0.30, "量能转移=资金流向"),
        ("trend_strength", 0.20, "趋势确认"),
        ("ma_alignment", 0.15, "均线排列=板块强度"),
    ],
    # Default for "unknown" or unmatched
    "_default": [
        ("momentum_score", 0.30, "通用动量"),
        ("trend_strength", 0.25, "通用趋势"),
        ("volatility", 0.25, "通用波动"),
        ("volume_ratio", 0.20, "通用量能"),
    ],
}


def _build_factor_model(style: str, theme: str = "", rationale: str = "") -> FactorModel:
    """Build factor model from investment style using predefined mappings."""
    factors = _STYLE_FACTOR_MAP.get(style, _STYLE_FACTOR_MAP["_default"])
    registry = _load_factors()

    result = FactorModel(
        theme=theme or f"{style}策略因子映射",
        rationale=rationale or f"基于投资风格 '{style}' 的规则映射",
        confidence=0.35 if style != "unknown" else 0.20,
        source="rule",
    )

    for name, weight, reason in factors:
        if name in registry:
            result.factors.append(FactorWeight(
                name=name, weight=weight, reason=reason,
                category=registry.get(name, ""),
            ))

    if not result.factors:
        # All factors missing from registry — use whatever is available
        for name, cat in list(registry.items())[:4]:
            result.factors.append(FactorWeight(
                name=name, weight=0.25, reason="通用因子(规则回退)",
                category=cat,
            ))

    # Normalize weights
    total = sum(f.weight for f in result.factors)
    if total > 0:
        for f in result.factors:
            f.weight = round(f.weight / total, 4)

    return result


# ═══════════════════════════════════════════════════════════
# LLM-based mapping
# ═══════════════════════════════════════════════════════════

def _build_llm_prompt(thesis_text: str, available_factors: str) -> str:
    return f"""You are a quantitative research analyst. Map the investment thesis below to specific technical factors.

Available factors (name: category - description):
{available_factors}

Investment thesis:
{thesis_text}

Return ONLY a JSON object:
{{
  "theme": "brief theme label",
  "factors": [
    {{"name": "factor_name", "weight": 0.35, "reason": "why this factor"}}
  ],
  "rationale": "why these factors were chosen (max 200 chars)"
}}

Rules:
- Use ONLY factor names from the available list above.
- Weights must sum to 1.0 (3-5 factors recommended).
- Each factor needs a specific reason tied to the thesis.
- Do not include any text outside the JSON."""


def _llm_map(thesis_text: str, style: str) -> FactorModel:
    """Use LLM to map thesis to factors. Falls back to rule-based on failure."""
    try:
        from src.ai.engine import LLMClient
        client = LLMClient()
        if not client.api_key:
            return _build_factor_model(style)

        registry = _load_factors()
        factor_list = "\n".join(
            f"  {n}: {c}"
            for n, c in sorted(registry.items())
        )
        prompt = _build_llm_prompt(thesis_text[:2000], factor_list)
        response = client.ask(prompt, temperature=0.1)

        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            return _build_factor_model(style)

        data = json.loads(json_match.group(0))
        result = FactorModel(
            theme=str(data.get("theme", "")),
            rationale=str(data.get("rationale", "")),
            confidence=0.65,
            source="llm",
        )

        for f in data.get("factors", []):
            name = str(f.get("name", ""))
            if name in registry:
                result.factors.append(FactorWeight(
                    name=name,
                    weight=float(f.get("weight", 0.0)),
                    reason=str(f.get("reason", "")),
                    category=registry[name],
                ))

        if result.factors:
            total = sum(f.weight for f in result.factors)
            if total > 0:
                for f in result.factors:
                    f.weight = round(f.weight / total, 4)
            return result

        return _build_factor_model(style)

    except Exception as e:
        _log.warning(f"LLM factor mapping failed: {e}")
        return _build_factor_model(style)


# ═══════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════

def map_thesis_to_factors(
    thesis=None,
    text: str = "",
    style: str = "unknown",
    use_llm: bool = True,
) -> FactorModel:
    """Map an investment thesis to quantitative factors.

    Args:
        thesis: InvestmentThesis object (from src.lxl_quantaxis.research.thesis)
        text: Free-text thesis description (used if thesis is None)
        style: Investment style override
        use_llm: Try LLM first (falls back to rule-based)

    Returns:
        FactorModel with concrete factor weights from FACTOR_REGISTRY
    """
    # Extract from thesis object if provided
    if thesis is not None:
        text = (
            f"{thesis.core_argument}\n"
            f"Bullish: {thesis.bullish_reasons}\n"
            f"Bearish: {thesis.bearish_reasons}\n"
            f"Risks: {thesis.key_risks}"
        )
        style = thesis.conviction_style if hasattr(thesis, 'conviction_style') else style
        if hasattr(thesis, 'investment_style') and thesis.investment_style:
            style = thesis.investment_style

    text = (text or "").strip()[:3000]
    style = style or "unknown"

    # Ensure registry is loaded
    _load_factors()

    if use_llm and text:
        model = _llm_map(text, style)
    else:
        model = _build_factor_model(style)

    # Validate
    if not model.validate():
        _log.warning("LLM model validation failed, falling back to rule-based")
        model = _build_factor_model(style)

    return model


def thesis_to_factor_dict(thesis=None, text: str = "", style: str = "") -> dict:
    """One-shot: thesis → factor dict for API/display."""
    model = map_thesis_to_factors(thesis=thesis, text=text, style=style)
    return model.to_dict()
