"""Strict validation for note-to-strategy extraction."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

ALLOWED_FEATURES = frozenset({"close", "ma20", "revenue_growth", "industry_growth", "valuation_pe", "volatility_20d"})
ALLOWED_OPERATORS = frozenset({">", ">=", "<", "<=", "crosses_above", "crosses_below"})
REQUIRED_KEYS = frozenset({"name", "thesis", "conditions", "exit_conditions", "risks", "unknowns", "evidence_spans"})


class StrategySchemaError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class EvidenceSpan:
    start: int
    end: int
    quote: str


def validate_strategy_payload(payload: object, *, note: str) -> Mapping[str, object]:
    if not isinstance(payload, Mapping) or set(payload) != REQUIRED_KEYS:
        raise StrategySchemaError("strategy payload has unknown or missing fields")
    if not isinstance(payload["name"], str) or not payload["name"].strip():
        raise StrategySchemaError("strategy name is required")
    if not isinstance(payload["thesis"], str) or not payload["thesis"].strip():
        raise StrategySchemaError("strategy thesis is required")
    _validate_rules(payload["conditions"])
    _validate_rules(payload["exit_conditions"])
    for field in ("risks", "unknowns"):
        values = payload[field]
        if not _is_string_sequence(values):
            raise StrategySchemaError(f"{field} must be a string array")
    _validate_spans(payload["evidence_spans"], note)
    return payload


def _validate_rules(value: object) -> None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise StrategySchemaError("conditions must be an array")
    for rule in value:
        if not isinstance(rule, Mapping) or set(rule) != {"feature", "operator", "value"}:
            raise StrategySchemaError("condition schema is invalid")
        if rule["feature"] not in ALLOWED_FEATURES:
            raise StrategySchemaError(f"feature is not allowed: {rule['feature']}")
        if rule["operator"] not in ALLOWED_OPERATORS:
            raise StrategySchemaError(f"operator is not allowed: {rule['operator']}")
        if isinstance(rule["value"], bool) or not isinstance(rule["value"], (int, float)):
            raise StrategySchemaError("condition value must be numeric")


def _validate_spans(value: object, note: str) -> None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise StrategySchemaError("at least one evidence span is required")
    for item in value:
        if not isinstance(item, Mapping) or set(item) != {"start", "end", "quote"}:
            raise StrategySchemaError("evidence span schema is invalid")
        start, end, quote = item["start"], item["end"], item["quote"]
        if not isinstance(start, int) or not isinstance(end, int) or not isinstance(quote, str):
            raise StrategySchemaError("evidence span types are invalid")
        if start < 0 or end <= start or note[start:end] != quote:
            raise StrategySchemaError("evidence span does not match the original note")


def _is_string_sequence(value: object) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and all(isinstance(item, str) and item.strip() for item in value)
    )
