"""Normalized financial-fact schema checks."""

import math

from src.lxl_quantaxis.data.providers import DataKind, PointInTimeRecord, SchemaViolation


def validate_financial_record(record: PointInTimeRecord) -> tuple[SchemaViolation, ...]:
    if record.kind is not DataKind.FINANCIAL:
        return (SchemaViolation("financial.kind", "record is not financial data"),)
    issues: list[SchemaViolation] = []
    if not isinstance(record.payload.get("metric"), str) or not record.payload["metric"]:
        issues.append(SchemaViolation("financial.metric", "metric must be a non-empty string"))
    value = record.payload.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        issues.append(SchemaViolation("financial.value", "value must be a finite number"))
    currency = record.payload.get("currency")
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha():
        issues.append(SchemaViolation("financial.currency", "currency must be a three-letter code"))
    period_end = record.payload.get("period_end")
    if not isinstance(period_end, str) or len(period_end) != 10:
        issues.append(SchemaViolation("financial.period_end", "period_end must use YYYY-MM-DD"))
    return tuple(issues)
