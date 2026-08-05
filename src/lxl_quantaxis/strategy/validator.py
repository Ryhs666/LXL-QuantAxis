"""StrategySpec validator — pre-compile safety and correctness checks."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationResult:
    valid: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
        }


# Whitelists
_ALLOWED_FACTOR_NAMES: frozenset[str] = frozenset()  # loaded lazily
_VALID_RISK_KEYS = frozenset({"max_drawdown_pct", "position_size_pct",
                               "stop_loss_pct", "max_single_pct", "trailing_stop_atr"})
_SAFE_NAME_PATTERN = re.compile(r'^[a-z][a-z0-9_.-]*$')
_BLOCKED_TOKENS = frozenset({"import", "exec", "eval", "open", "__", "os.",
                              "sys.", "subprocess", "lambda", "class ", "def ",
                              "globals", "locals", "getattr", "setattr"})

# Standard data column names — not factors, don't validate against registry
_DATA_COLUMNS = frozenset({"open", "high", "low", "close", "volume", "amount",
                            "date", "vwap", "returns", "price"})


def _load_factor_names() -> frozenset[str]:
    global _ALLOWED_FACTOR_NAMES
    if not _ALLOWED_FACTOR_NAMES:
        try:
            from src.factors.definitions import FACTOR_REGISTRY
            _ALLOWED_FACTOR_NAMES = frozenset(FACTOR_REGISTRY.keys())
        except ImportError:
            _ALLOWED_FACTOR_NAMES = frozenset()
    return _ALLOWED_FACTOR_NAMES


def _extract_names(rule: str) -> set[str]:
    """Extract variable names from a rule expression using AST."""
    try:
        tree = ast.parse(rule.strip(), mode="eval")
        return {
            node.id for node in ast.walk(tree)
            if isinstance(node, ast.Name) and not node.id.startswith("_")
        }
    except SyntaxError:
        return set()


def _is_safe_rule(rule: str) -> bool:
    lower = rule.lower()
    return not any(tok in lower for tok in _BLOCKED_TOKENS)


def _check_factor_exists(name: str, result: ValidationResult) -> None:
    factors = _load_factor_names()
    if not factors:
        result.warnings.append("Unable to load FACTOR_REGISTRY for validation")
        return
    if name not in factors:
        result.errors.append(f"Factor '{name}' not found in FACTOR_REGISTRY")
        if factors:
            import difflib
            close = difflib.get_close_matches(name, factors, n=3)
            if close:
                result.suggestions.append(f"Did you mean: {', '.join(close)}?")


def validate_strategy_spec(spec) -> ValidationResult:
    """Validate a StrategySpec before compilation.

    Checks:
      1. Rule syntax (valid Python expressions)
      2. Factor existence (names in FACTOR_REGISTRY)
      3. Data availability (known column names)
      4. Parameter ranges
      5. Risk rule legality
    """
    result = ValidationResult(valid=True)

    # 1. Name check
    if not spec.name or not spec.name.strip():
        result.errors.append("Strategy name is empty")
    if not _SAFE_NAME_PATTERN.match(spec.strategy_id):
        result.errors.append(f"Strategy ID '{spec.strategy_id}' is not a safe identifier")

    # 2. Rule syntax check
    for label, rule in [("entry", spec.entry_rule), ("exit", spec.exit_rule)]:
        if not rule or not rule.strip():
            result.errors.append(f"{label}_rule is empty")
            continue
        if not _is_safe_rule(rule):
            result.errors.append(f"{label}_rule contains blocked tokens")
            continue
        try:
            ast.parse(rule.strip(), mode="eval")
        except SyntaxError as e:
            result.errors.append(f"{label}_rule syntax error: {e}")
            continue

        # Check factor names in rule (skip data columns like 'close')
        names = _extract_names(rule)
        for name in names:
            if name not in _DATA_COLUMNS:
                _check_factor_exists(name, result)

    # 3. Data requirements
    known_data = frozenset({"open", "high", "low", "close", "volume", "amount", "date"})
    for req in spec.data_requirements:
        if req not in known_data:
            result.warnings.append(f"Data requirement '{req}' is not a standard OHLCV column")

    # 4. Parameter validation
    for param in spec.parameters:
        if param.minimum is not None and param.maximum is not None and param.minimum > param.maximum:
            result.errors.append(f"Parameter '{param.name}': min > max")
        try:
            param.validate(param.default)
        except ValueError as e:
            result.errors.append(f"Parameter '{param.name}' default invalid: {e}")

    # 5. Risk rule validation (for AI strategies)
    if spec.source == "ai":
        if not spec.description:
            result.warnings.append("AI-generated strategy has no description")
        if "max_drawdown" not in spec.exit_rule.lower():
            result.warnings.append("AI strategy should include a max_drawdown exit condition")

    # Final
    if result.errors:
        result.valid = False

    return result
