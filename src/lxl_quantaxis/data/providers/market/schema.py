"""Normalized market-bar schema checks."""

import math

from src.lxl_quantaxis.data.providers import DataKind, PointInTimeRecord, SchemaViolation


def validate_market_record(record: PointInTimeRecord) -> tuple[SchemaViolation, ...]:
    if record.kind is not DataKind.MARKET:
        return (SchemaViolation("market.kind", "record is not market data"),)
    issues: list[SchemaViolation] = []
    values: dict[str, float] = {}
    for field in ("open", "high", "low", "close", "volume"):
        value = record.payload.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            issues.append(SchemaViolation(f"market.{field}", f"{field} must be a finite number"))
        else:
            values[field] = float(value)
    if len(values) == 5:
        if values["high"] < max(values["open"], values["low"], values["close"]):
            issues.append(SchemaViolation("market.price_bounds", "high is below an observed price"))
        if values["low"] > min(values["open"], values["high"], values["close"]):
            issues.append(SchemaViolation("market.price_bounds", "low is above an observed price"))
        if values["volume"] < 0:
            issues.append(SchemaViolation("market.volume", "volume cannot be negative"))
    adjustment = record.payload.get("adjustment_factor", 1.0)
    if isinstance(adjustment, bool) or not isinstance(adjustment, (int, float)) or float(adjustment) <= 0:
        issues.append(SchemaViolation("market.adjustment_factor", "adjustment_factor must be positive"))
    return tuple(issues)
