"""Company-research domain models."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class CompanyResearch:
    symbol: str
    name: str
    exchange: str
    sector: str
    industry: str
    description: str
    data_as_of: date
    investment_case: tuple[str, ...]
    bear_case: tuple[str, ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.symbol.strip() or not self.name.strip() or not self.exchange.strip():
            raise ValueError("company identity fields cannot be empty")
        if not self.industry.strip() or not self.description.strip():
            raise ValueError("company industry and description cannot be empty")
        if not self.investment_case or not self.bear_case:
            raise ValueError("company research requires a thesis and a bear case")
