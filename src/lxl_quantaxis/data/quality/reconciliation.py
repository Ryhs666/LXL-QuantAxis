"""Cross-provider sample reconciliation."""

from __future__ import annotations

from collections.abc import Sequence

from src.lxl_quantaxis.data.providers import PointInTimeRecord
from src.lxl_quantaxis.data.quality.models import IssueSeverity, QualityIssue


def reconcile_numeric_field(
    records: Sequence[PointInTimeRecord],
    *,
    field: str,
    relative_tolerance: float,
) -> tuple[QualityIssue, ...]:
    if relative_tolerance < 0:
        raise ValueError("relative_tolerance cannot be negative")
    grouped: dict[str, list[tuple[PointInTimeRecord, float]]] = {}
    for record in records:
        value = record.payload.get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            grouped.setdefault(record.logical_key, []).append((record, float(value)))
    issues: list[QualityIssue] = []
    for logical_key, samples in grouped.items():
        if len(samples) < 2:
            continue
        values = [value for _, value in samples]
        denominator = max(abs(min(values)), abs(max(values)), 1e-12)
        spread = (max(values) - min(values)) / denominator
        if spread > relative_tolerance:
            record = samples[0][0]
            providers = ", ".join(sorted(sample.provider for sample, _ in samples))
            issues.append(
                QualityIssue(
                    code=f"reconciliation.{field}",
                    message=f"{field} differs across providers {providers}",
                    severity=IssueSeverity.WARNING,
                    logical_key=logical_key,
                    provider=providers,
                )
            )
    return tuple(issues)
