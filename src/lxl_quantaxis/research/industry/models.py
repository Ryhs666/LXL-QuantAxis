"""Industry-research domain models."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class IndustryResearch:
    name: str
    data_as_of: date
    cycle: str
    growth_rate: Decimal | None
    growth_drivers: tuple[str, ...]
    competitive_factors: tuple[str, ...]
    risks: tuple[str, ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.cycle.strip():
            raise ValueError("industry name and cycle cannot be empty")
        if self.growth_rate is not None and self.growth_rate <= Decimal("-1"):
            raise ValueError("industry growth rate must be expressed as a ratio above -1")
        if not self.growth_drivers or not self.risks:
            raise ValueError("industry research requires drivers and risks")
