"""Deterministic Markdown rendering for research packages."""

from __future__ import annotations

from decimal import Decimal

from src.lxl_quantaxis.research.application import ResearchPackage


def render_markdown(package: ResearchPackage) -> str:
    company_name = package.company.name if package.company else "Company data unavailable"
    valuation = "Unavailable"
    if package.valuation is not None:
        estimate = package.valuation
        valuation = (
            f"{_decimal(estimate.fair_value.amount)} {estimate.fair_value.currency}/share ({estimate.method.value})"
        )
    lines = [
        f"# {company_name} ({package.symbol}) Equity Research",
        "",
        f"- Status: {package.status.value}",
        f"- Data as of: {package.data_as_of.isoformat()}",
        f"- Generated at: {package.generated_at.isoformat()}",
        f"- Valuation: {valuation}",
        "",
        "## Investment case",
        *_bullets(package.investment_case),
        "",
        "## Bear case",
        *_bullets(package.bear_case),
        "",
        "## Risks",
        *_bullets(package.risks),
        "",
        "## Open questions",
        *_bullets(package.open_questions),
        "",
        "## Evidence",
        *(
            f"- [{item.evidence_id}] {item.source}: {item.title} "
            f"(as of {item.as_of.isoformat()}){f' — {item.locator}' if item.locator else ''}"
            for item in package.evidence
        ),
    ]
    if package.missing_sections or package.evidence_findings:
        lines.extend(
            [
                "",
                "## Data quality",
                *(_bullets(tuple(f"Missing section: {name}" for name in package.missing_sections))),
                *_bullets(package.evidence_findings),
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _bullets(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(f"- {value}" for value in values) or ("- None",)


def _decimal(value: Decimal) -> str:
    return format(value.normalize(), "f")
