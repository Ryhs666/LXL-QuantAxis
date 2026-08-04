"""Evidence contracts shared by the equity-research workspace."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Evidence:
    """A citable fact source with an explicit information date."""

    evidence_id: str
    source: str
    title: str
    as_of: date
    locator: str = ""

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("evidence_id cannot be empty")
        if not self.source.strip() or not self.title.strip():
            raise ValueError("evidence source and title cannot be empty")


def evidence_gaps(
    evidence: tuple[Evidence, ...], referenced_ids: tuple[str, ...], *, data_as_of: date
) -> tuple[str, ...]:
    """Return deterministic evidence-quality findings for a package."""

    findings: list[str] = []
    ids = [item.evidence_id for item in evidence]
    duplicates = sorted({evidence_id for evidence_id in ids if ids.count(evidence_id) > 1})
    findings.extend(f"duplicate evidence id: {evidence_id}" for evidence_id in duplicates)
    known = set(ids)
    findings.extend(f"missing evidence: {evidence_id}" for evidence_id in sorted(set(referenced_ids) - known))
    findings.extend(
        f"future-dated evidence: {item.evidence_id}"
        for item in sorted(evidence, key=lambda value: value.evidence_id)
        if item.as_of > data_as_of
    )
    return tuple(findings)
