"""AI Strategy Builder — FactorModel → StrategySpec DSL.

Converts factor models into validated StrategySpec objects using a
declarative DSL.  NO code generation, NO exec/eval.

The builder produces rules that the existing V2 strategy compiler
can consume.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from src.lxl_quantaxis.core.logging import get_logger

_log = get_logger("research.strategy_builder")

# ── Schema validation constants ──
VALID_ACTIONS = frozenset({"BUY", "SELL", "HOLD"})
VALID_RISK_RULES = frozenset({
    "max_drawdown_pct", "position_size_pct", "stop_loss_pct",
    "max_single_pct", "trailing_stop_atr",
})
MAX_RULE_LENGTH = 500


# ═══════════════════════════════════════════════════════════
# Strategy blueprint (DSL output, not Python code)
# ═══════════════════════════════════════════════════════════

@dataclass
class StrategyBlueprint:
    """Declarative strategy definition — safe, serializable, no code."""

    name: str = ""
    description: str = ""
    universe: str = "A股"

    # Entry rules: list of "factor_name OPERATOR threshold" strings
    entry_conditions: list[str] = field(default_factory=list)
    entry_logic: str = "AND"  # AND | OR | WEIGHTED_score

    # Exit rules
    exit_conditions: list[str] = field(default_factory=list)
    exit_logic: str = "OR"

    # Risk rules
    risk_rules: dict[str, float] = field(default_factory=dict)
    position_rules: dict[str, float] = field(default_factory=dict)

    # Factor weights from model
    factor_weights: list[dict] = field(default_factory=list)

    # Metadata
    source: str = "rule"
    confidence: float = 0.0

    def validate(self) -> bool:
        """Basic schema validation."""
        if not self.name.strip():
            return False
        for cond in self.entry_conditions + self.exit_conditions:
            if len(cond) > MAX_RULE_LENGTH:
                return False
            if not _is_safe_rule(cond):
                return False
        if self.entry_logic not in ("AND", "OR", "WEIGHTED_score"):
            return False
        if self.exit_logic not in ("AND", "OR", "WEIGHTED_score"):
            return False
        for k, v in self.risk_rules.items():
            if k not in VALID_RISK_RULES:
                return False
            if not (0 <= v <= 100):
                return False
        return True

    def to_strategy_spec(self):
        """Convert to V2 StrategySpec (requires strategy module)."""
        from src.lxl_quantaxis.strategy.base.spec import StrategySpec

        safe_id = re.sub(r'[^a-z0-9_.-]', '', self.name.lower().replace(' ', '_'))
        safe_id = safe_id.strip('_.-')[:30]
        if not safe_id or not any(c.isalnum() for c in safe_id):
            safe_id = f"strategy_{abs(hash(self.name)) % 100000:05d}"
        strategy_id = f"ai.{safe_id}"

        entry = f" {self.entry_logic} ".join(
            f"({c})" for c in self.entry_conditions
        ) if self.entry_conditions else "close > 0"

        exit_rule = f" {self.exit_logic} ".join(
            f"({c})" for c in self.exit_conditions
        ) if self.exit_conditions else "close < 0"

        return StrategySpec(
            strategy_id=strategy_id,
            version="1.0.0",
            name=self.name[:80],
            description=self.description[:200],
            entry_rule=entry[:MAX_RULE_LENGTH],
            exit_rule=exit_rule[:MAX_RULE_LENGTH],
            data_requirements=("close", "high", "low", "volume"),
            source="ai" if self.source == "llm" else "ai",
        )


def _is_safe_rule(rule: str) -> bool:
    """Check that a rule string is safe DSL, not executable code."""
    blocked = ["import", "__", "exec", "eval", "open", "os.", "sys.",
               "subprocess", "class ", "def ", "lambda", ";", "\\"]
    lower = rule.lower()
    return not any(b in lower for b in blocked)


# ═══════════════════════════════════════════════════════════
# Rule-based builder
# ═══════════════════════════════════════════════════════════

def _build_from_style(
    theme: str, style: str, factors: list[dict], bullish: str, bearish: str
) -> StrategyBlueprint:
    """Build strategy blueprint from investment style using predefined templates."""

    bp = StrategyBlueprint(
        name=theme or f"{style}_strategy",
        description=f"{style}策略 — 基于因子模型的自动构建",
        source="rule",
        confidence=0.35,
    )

    # Entry conditions based on factor weights
    entry_parts = []
    for fw in factors[:4]:
        name = fw.get("name", "")
        weight = fw.get("weight", 0)
        cat = fw.get("category", "")
        # Map factor to a threshold rule
        if cat in ("momentum", "trend"):
            entry_parts.append(f"{name} > 0.6")
        elif cat in ("volatility",):
            entry_parts.append(f"{name} < 0.4")
        else:
            entry_parts.append(f"{name} > 0.5")

    bp.entry_conditions = entry_parts
    bp.entry_logic = "AND" if len(entry_parts) <= 2 else "WEIGHTED_score"

    # Exit: drawdown-based
    bp.exit_conditions = ["max_drawdown > 0.10"]
    bp.exit_logic = "OR"

    # Risk rules
    bp.risk_rules = {
        "max_drawdown_pct": 10.0,
        "position_size_pct": 20.0,
        "stop_loss_pct": 5.0,
    }
    bp.position_rules = {
        "max_single_pct": 15.0,
    }

    # Factor weights
    bp.factor_weights = factors[:6]

    return bp


# ═══════════════════════════════════════════════════════════
# LLM-based builder
# ═══════════════════════════════════════════════════════════

def _build_llm_prompt(theme: str, style: str, factors: list[dict]) -> str:
    factor_desc = "\n".join(
        f"  {f['name']} ({f.get('category','')}, weight={f.get('weight',0):.2f})"
        for f in factors[:6]
    )
    return f"""You are a quantitative strategy designer. Build a trading strategy from these factors.

Theme: {theme or style}
Style: {style}
Factors:
{factor_desc}

Return ONLY a JSON object:
{{
  "name": "strategy name",
  "description": "what this strategy does",
  "entry_conditions": ["factor_name > 0.6", "factor_name < 0.3"],
  "entry_logic": "AND|OR|WEIGHTED_score",
  "exit_conditions": ["max_drawdown > 0.10"],
  "exit_logic": "OR",
  "risk_rules": {{"max_drawdown_pct": 10, "stop_loss_pct": 5}},
  "position_rules": {{"position_size_pct": 20, "max_single_pct": 15}}
}}

Rules:
- entry/exit conditions use ONLY the factor names above.
- Operators: >, <, >=, <= only.
- risk_rules keys: max_drawdown_pct, position_size_pct, stop_loss_pct, max_single_pct, trailing_stop_atr
- All values must be numeric.
- Do NOT include text outside the JSON."""


def _llm_build(theme: str, style: str, factors: list[dict]) -> StrategyBlueprint:
    """Use LLM to build strategy. Falls back to rule-based on failure."""
    try:
        from src.ai.engine import LLMClient
        client = LLMClient()
        if not client.api_key:
            return _build_from_style(theme, style, factors, "", "")

        prompt = _build_llm_prompt(theme, style, factors)
        response = client.ask(prompt, temperature=0.1)

        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            return _build_from_style(theme, style, factors, "", "")

        data = json.loads(json_match.group(0))
        bp = StrategyBlueprint(
            name=str(data.get("name", theme or ""))[:80],
            description=str(data.get("description", ""))[:200],
            entry_conditions=_safe_list(data.get("entry_conditions", [])),
            entry_logic=str(data.get("entry_logic", "AND")),
            exit_conditions=_safe_list(data.get("exit_conditions", [])),
            exit_logic=str(data.get("exit_logic", "OR")),
            risk_rules=_safe_float_dict(data.get("risk_rules", {})),
            position_rules=_safe_float_dict(data.get("position_rules", {})),
            source="llm",
            confidence=0.65,
        )
        if bp.validate():
            return bp
    except Exception as e:
        _log.warning(f"LLM strategy build failed: {e}")

    return _build_from_style(theme, style, factors, "", "")


def _safe_list(raw) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(x)[:MAX_RULE_LENGTH] for x in raw if isinstance(x, str) and _is_safe_rule(str(x))]


def _safe_float_dict(raw) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    result = {}
    for k, v in raw.items():
        if k in VALID_RISK_RULES:
            try:
                val = float(v)
                if 0 <= val <= 100:
                    result[str(k)] = val
            except (ValueError, TypeError):
                pass
    return result


# ═══════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════

def build_strategy(
    factor_model=None,
    theme: str = "",
    style: str = "unknown",
    factors: list[dict] = None,
    bullish: str = "",
    bearish: str = "",
    use_llm: bool = True,
) -> StrategyBlueprint:
    """Build a strategy blueprint from a factor model.

    Args:
        factor_model: FactorModel object (from factor_mapper)
        theme: Investment theme label
        style: Investment style
        factors: List of {name, weight, category} dicts
        use_llm: Try LLM first (falls back to rule-based)

    Returns:
        StrategyBlueprint that can be converted to StrategySpec
    """
    if factor_model is not None:
        theme = factor_model.theme or theme
        factors = [
            {"name": f.name, "weight": f.weight, "category": f.category}
            for f in (factor_model.factors or [])
        ]
        style = style or "unknown"

    factors = factors or []
    theme = theme or style

    if not factors:
        factors = [{"name": "momentum_score", "weight": 1.0, "category": "momentum"}]

    if use_llm:
        bp = _llm_build(theme, style, factors)
    else:
        bp = _build_from_style(theme, style, factors, bullish, bearish)

    if not bp.validate():
        _log.warning("Strategy blueprint validation failed, using safe fallback")
        bp = _build_from_style(theme, style, factors, bullish, bearish)

    bp.factor_weights = factors[:6]
    return bp


def build_and_compile(
    factor_model=None,
    theme: str = "",
    style: str = "unknown",
    use_llm: bool = True,
):
    """Build strategy AND compile to V2 StrategySpec.

    Returns a valid StrategySpec ready for the strategy registry.
    """
    bp = build_strategy(
        factor_model=factor_model, theme=theme, style=style, use_llm=use_llm,
    )
    return bp.to_strategy_spec()
