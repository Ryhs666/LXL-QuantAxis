"""Application service that assembles an evidence-backed equity-research package."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Generic, Protocol, TypeVar

from src.lxl_quantaxis.research.company import CompanyResearch
from src.lxl_quantaxis.research.evidence import Evidence, evidence_gaps
from src.lxl_quantaxis.research.financial import FinancialResearch
from src.lxl_quantaxis.research.industry import IndustryResearch
from src.lxl_quantaxis.research.valuation import ValuationEstimate, forward_pe_valuation

T = TypeVar("T", covariant=True)


@dataclass(frozen=True, slots=True)
class Sourced(Generic[T]):
    content: T
    evidence: tuple[Evidence, ...]


class CompanyResearchProvider(Protocol):
    def get_company(self, *, symbol: str, as_of: date) -> Sourced[CompanyResearch] | None: ...


class IndustryResearchProvider(Protocol):
    def get_industry(self, *, symbol: str, industry: str, as_of: date) -> Sourced[IndustryResearch] | None: ...


class FinancialResearchProvider(Protocol):
    def get_financials(self, *, symbol: str, as_of: date) -> Sourced[FinancialResearch] | None: ...


class ResearchStatus(StrEnum):
    COMPLETE = "complete"
    DEGRADED = "degraded"


@dataclass(frozen=True, slots=True)
class ResearchPackage:
    symbol: str
    generated_at: datetime
    data_as_of: date
    status: ResearchStatus
    company: CompanyResearch | None
    industry: IndustryResearch | None
    financials: FinancialResearch | None
    valuation: ValuationEstimate | None
    investment_case: tuple[str, ...]
    bear_case: tuple[str, ...]
    risks: tuple[str, ...]
    open_questions: tuple[str, ...]
    evidence: tuple[Evidence, ...]
    missing_sections: tuple[str, ...]
    evidence_findings: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("research symbol cannot be empty")
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        if self.generated_at.date() < self.data_as_of:
            raise ValueError("research cannot be generated before its data-as-of date")
        if self.status is ResearchStatus.COMPLETE and (self.missing_sections or self.evidence_findings):
            raise ValueError("complete research cannot contain data-quality findings")


@dataclass(frozen=True, slots=True)
class EquityResearchService:
    company_provider: CompanyResearchProvider
    industry_provider: IndustryResearchProvider
    financial_provider: FinancialResearchProvider
    target_pe: Decimal

    def __post_init__(self) -> None:
        if self.target_pe <= 0:
            raise ValueError("target P/E must be positive")

    def build(self, *, symbol: str, as_of: date, generated_at: datetime) -> ResearchPackage:
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("symbol cannot be empty")

        company_result = self.company_provider.get_company(symbol=normalized_symbol, as_of=as_of)
        industry_result = None
        if company_result is not None:
            industry_result = self.industry_provider.get_industry(
                symbol=normalized_symbol,
                industry=company_result.content.industry,
                as_of=as_of,
            )
        financial_result = self.financial_provider.get_financials(symbol=normalized_symbol, as_of=as_of)

        company = company_result.content if company_result else None
        industry = industry_result.content if industry_result else None
        financials = financial_result.content if financial_result else None
        valuation = self._value(financials, as_of)
        evidence = _merge_evidence(company_result, industry_result, financial_result)
        referenced_ids = _referenced_ids(company, industry, financials, valuation)
        findings = list(evidence_gaps(evidence, referenced_ids, data_as_of=as_of))
        findings.extend(_section_date_findings(company, industry, financials, valuation, as_of))
        findings.extend(_section_evidence_findings(company, industry, financials, valuation))

        missing = []
        if company is None:
            missing.append("company")
        if industry is None:
            missing.append("industry")
        if financials is None:
            missing.append("financials")
        if valuation is None:
            missing.append("valuation")

        investment_case = () if company is None else company.investment_case
        if financials is not None:
            investment_case = (*investment_case, *financials.findings)
        bear_case = () if company is None else company.bear_case
        risks = () if industry is None else industry.risks
        open_questions = ["What evidence would invalidate the investment case?"]
        open_questions.extend(f"What data is needed to complete the {name} section?" for name in missing)
        status = ResearchStatus.DEGRADED if missing or findings else ResearchStatus.COMPLETE
        return ResearchPackage(
            symbol=normalized_symbol,
            generated_at=generated_at,
            data_as_of=as_of,
            status=status,
            company=company,
            industry=industry,
            financials=financials,
            valuation=valuation,
            investment_case=investment_case,
            bear_case=bear_case,
            risks=risks,
            open_questions=tuple(open_questions),
            evidence=evidence,
            missing_sections=tuple(missing),
            evidence_findings=tuple(sorted(set(findings))),
        )

    def _value(self, financials: FinancialResearch | None, as_of: date) -> ValuationEstimate | None:
        if (
            financials is None
            or financials.latest.available_on > as_of
            or financials.latest.earnings_per_share.amount <= 0
        ):
            return None
        return forward_pe_valuation(
            earnings_per_share=financials.latest.earnings_per_share,
            target_multiple=self.target_pe,
            data_as_of=financials.latest.available_on,
            evidence_ids=financials.evidence_ids,
        )


def _merge_evidence(*results: Sourced[object] | None) -> tuple[Evidence, ...]:
    items = (evidence for result in results if result is not None for evidence in result.evidence)
    return tuple(sorted(items, key=lambda item: item.evidence_id))


def _referenced_ids(
    company: CompanyResearch | None,
    industry: IndustryResearch | None,
    financials: FinancialResearch | None,
    valuation: ValuationEstimate | None,
) -> tuple[str, ...]:
    sections = (company, industry, financials, valuation)
    return tuple(evidence_id for section in sections if section is not None for evidence_id in section.evidence_ids)


def _section_date_findings(
    company: CompanyResearch | None,
    industry: IndustryResearch | None,
    financials: FinancialResearch | None,
    valuation: ValuationEstimate | None,
    as_of: date,
) -> tuple[str, ...]:
    dated_sections = (
        ("company", None if company is None else company.data_as_of),
        ("industry", None if industry is None else industry.data_as_of),
        ("financials", None if financials is None else financials.data_as_of),
        ("valuation", None if valuation is None else valuation.data_as_of),
    )
    return tuple(
        f"future-dated section: {name}"
        for name, section_date in dated_sections
        if section_date is not None and section_date > as_of
    )


def _section_evidence_findings(
    company: CompanyResearch | None,
    industry: IndustryResearch | None,
    financials: FinancialResearch | None,
    valuation: ValuationEstimate | None,
) -> tuple[str, ...]:
    sections = (
        ("company", company),
        ("industry", industry),
        ("financials", financials),
        ("valuation", valuation),
    )
    return tuple(
        f"section has no evidence references: {name}"
        for name, section in sections
        if section is not None and not section.evidence_ids
    )
