"""Tests for evidence-backed equity research assembly and degradation."""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from src.lxl_quantaxis.core.contracts.money import Money
from src.lxl_quantaxis.research import (
    CompanyResearchProvider,
    EquityResearchService,
    Evidence,
    ResearchStatus,
    Sourced,
)
from src.lxl_quantaxis.research.company import CompanyResearch
from src.lxl_quantaxis.research.financial import FinancialPeriod, FinancialResearch
from src.lxl_quantaxis.research.industry import IndustryResearch
from src.lxl_quantaxis.research.reports import render_markdown
from src.lxl_quantaxis.research.valuation import ValuationUnit, forward_pe_valuation

AS_OF = date(2025, 12, 31)
GENERATED_AT = datetime(2026, 1, 2, 9, 0, tzinfo=timezone(timedelta(hours=8)))


class FixtureCompanyProvider:
    def __init__(self, *, evidence_id: str = "company-1") -> None:
        self.evidence_id = evidence_id

    def get_company(self, *, symbol: str, as_of: date) -> Sourced[CompanyResearch] | None:
        return Sourced(
            CompanyResearch(
                symbol=symbol,
                name="LXL Technology",
                exchange="SSE",
                sector="Information Technology",
                industry="Computing Infrastructure",
                description="Enterprise computing equipment provider.",
                data_as_of=as_of,
                investment_case=("Enterprise demand is expanding.",),
                bear_case=("Demand may normalize.",),
                evidence_ids=(self.evidence_id,),
            ),
            (Evidence("company-1", "Exchange filing", "Annual report", as_of, "p. 12"),),
        )


class FixtureIndustryProvider:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available

    def get_industry(self, *, symbol: str, industry: str, as_of: date) -> Sourced[IndustryResearch] | None:
        del symbol
        if not self.available:
            return None
        return Sourced(
            IndustryResearch(
                name=industry,
                data_as_of=as_of,
                cycle="expansion",
                growth_rate=Decimal("0.12"),
                growth_drivers=("AI infrastructure investment",),
                competitive_factors=("R&D scale",),
                risks=("Capital spending is cyclical.",),
                evidence_ids=("industry-1",),
            ),
            (Evidence("industry-1", "Industry association", "Market outlook", as_of),),
        )


class FixtureFinancialProvider:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available

    def get_financials(self, *, symbol: str, as_of: date) -> Sourced[FinancialResearch] | None:
        del symbol, as_of
        if not self.available:
            return None
        period = FinancialPeriod(
            period_end=date(2024, 12, 31),
            available_on=date(2025, 4, 30),
            revenue=Money.of("1000", "CNY"),
            net_income=Money.of("50", "CNY"),
            operating_cash_flow=Money.of("65", "CNY"),
            equity=Money.of("500", "CNY"),
            diluted_shares=Decimal("10"),
        )
        return Sourced(
            FinancialResearch(
                periods=(period,),
                findings=("Cash conversion remains healthy.",),
                evidence_ids=("financial-1",),
            ),
            (Evidence("financial-1", "Exchange filing", "FY2024 results", date(2025, 4, 30)),),
        )


def _service(
    *,
    company_provider: CompanyResearchProvider | None = None,
    industry_available: bool = True,
    financial_available: bool = True,
) -> EquityResearchService:
    return EquityResearchService(
        company_provider=company_provider or FixtureCompanyProvider(),
        industry_provider=FixtureIndustryProvider(available=industry_available),
        financial_provider=FixtureFinancialProvider(available=financial_available),
        target_pe=Decimal("20"),
    )


class EquityResearchServiceTests(unittest.TestCase):
    def test_complete_package_has_thesis_bear_case_and_complete_evidence(self) -> None:
        package = _service().build(symbol=" 600000 ", as_of=AS_OF, generated_at=GENERATED_AT)

        self.assertEqual(package.symbol, "600000")
        self.assertIs(package.status, ResearchStatus.COMPLETE)
        self.assertEqual(package.missing_sections, ())
        self.assertEqual(package.evidence_findings, ())
        self.assertEqual(len(package.evidence), 3)
        self.assertIn("Enterprise demand is expanding.", package.investment_case)
        self.assertEqual(package.bear_case, ("Demand may normalize.",))
        self.assertTrue(package.open_questions)

    def test_report_matches_fixed_fixture(self) -> None:
        package = _service().build(symbol="600000", as_of=AS_OF, generated_at=GENERATED_AT)
        fixture = Path(__file__).with_name("fixtures").joinpath("complete_report.md").read_text(encoding="utf-8")

        self.assertEqual(render_markdown(package), fixture)

    def test_missing_data_degrades_with_explicit_questions(self) -> None:
        package = _service(industry_available=False, financial_available=False).build(
            symbol="600000", as_of=AS_OF, generated_at=GENERATED_AT
        )

        self.assertIs(package.status, ResearchStatus.DEGRADED)
        self.assertEqual(package.missing_sections, ("industry", "financials", "valuation"))
        self.assertIn("What data is needed to complete the financials section?", package.open_questions)
        self.assertIsNone(package.valuation)

    def test_missing_evidence_reference_degrades_otherwise_complete_package(self) -> None:
        package = _service(company_provider=FixtureCompanyProvider(evidence_id="company-missing")).build(
            symbol="600000", as_of=AS_OF, generated_at=GENERATED_AT
        )

        self.assertIs(package.status, ResearchStatus.DEGRADED)
        self.assertEqual(package.evidence_findings, ("missing evidence: company-missing",))

    def test_section_without_evidence_references_is_not_marked_complete(self) -> None:
        result = FixtureCompanyProvider().get_company(symbol="600000", as_of=AS_OF)
        assert result is not None

        class UncitedCompanyProvider:
            def get_company(self, *, symbol: str, as_of: date) -> Sourced[CompanyResearch] | None:
                del symbol, as_of
                return Sourced(replace(result.content, evidence_ids=()), result.evidence)

        package = _service(company_provider=UncitedCompanyProvider()).build(
            symbol="600000", as_of=AS_OF, generated_at=GENERATED_AT
        )
        self.assertIn("section has no evidence references: company", package.evidence_findings)

    def test_future_dated_section_is_flagged(self) -> None:
        result = FixtureCompanyProvider().get_company(symbol="600000", as_of=AS_OF)
        assert result is not None

        class FutureCompanyProvider:
            def get_company(self, *, symbol: str, as_of: date) -> Sourced[CompanyResearch] | None:
                del symbol, as_of
                return Sourced(replace(result.content, data_as_of=date(2026, 1, 1)), result.evidence)

        package = _service(company_provider=FutureCompanyProvider()).build(
            symbol="600000", as_of=AS_OF, generated_at=GENERATED_AT
        )
        self.assertIn("future-dated section: company", package.evidence_findings)

    def test_loss_making_company_degrades_instead_of_using_pe_valuation(self) -> None:
        base = FixtureFinancialProvider().get_financials(symbol="600000", as_of=AS_OF)
        assert base is not None
        loss_period = replace(base.content.latest, net_income=Money.of("-50", "CNY"))

        class LossFinancialProvider:
            def get_financials(self, *, symbol: str, as_of: date) -> Sourced[FinancialResearch] | None:
                del symbol, as_of
                return Sourced(replace(base.content, periods=(loss_period,)), base.evidence)

        service = EquityResearchService(
            company_provider=FixtureCompanyProvider(),
            industry_provider=FixtureIndustryProvider(),
            financial_provider=LossFinancialProvider(),
            target_pe=Decimal("20"),
        )
        package = service.build(symbol="600000", as_of=AS_OF, generated_at=GENERATED_AT)

        self.assertIs(package.status, ResearchStatus.DEGRADED)
        self.assertIsNone(package.valuation)
        self.assertIn("valuation", package.missing_sections)


class ValuationUnitTests(unittest.TestCase):
    def test_forward_pe_returns_currency_per_share_without_unit_conversion(self) -> None:
        estimate = forward_pe_valuation(
            earnings_per_share=Money.of("5", "CNY"),
            target_multiple=Decimal("20"),
            data_as_of=AS_OF,
            evidence_ids=("financial-1",),
        )

        self.assertEqual(estimate.fair_value, Money.of("100", "CNY"))
        self.assertIs(estimate.unit, ValuationUnit.PER_SHARE)

    def test_forward_pe_rejects_non_positive_multiple(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be positive"):
            forward_pe_valuation(
                earnings_per_share=Money.of("5", "CNY"),
                target_multiple=Decimal("0"),
                data_as_of=AS_OF,
                evidence_ids=(),
            )


if __name__ == "__main__":
    unittest.main()
