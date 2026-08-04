"""Evidence-backed equity research workspace."""

from src.lxl_quantaxis.research.application import (
    CompanyResearchProvider,
    EquityResearchService,
    FinancialResearchProvider,
    IndustryResearchProvider,
    ResearchPackage,
    ResearchStatus,
    Sourced,
)
from src.lxl_quantaxis.research.evidence import Evidence

__all__ = [
    "CompanyResearchProvider",
    "EquityResearchService",
    "Evidence",
    "FinancialResearchProvider",
    "IndustryResearchProvider",
    "ResearchPackage",
    "ResearchStatus",
    "Sourced",
]
