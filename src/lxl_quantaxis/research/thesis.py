"""Investment thesis builder — structured thinking framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.lxl_quantaxis.research.notebook import create_note


@dataclass
class InvestmentThesis:
    """Structured investment thesis for a single security or market view.

    Maps directly to ResearchNote fields for persistence.
    """

    symbol: str = ""
    title: str = ""
    core_argument: str = ""       # → investment_thesis
    bullish_reasons: str = ""     # → bull_case
    bearish_reasons: str = ""     # → bear_case
    key_risks: str = ""           # → risk
    catalysts: str = ""           # what could move the price
    valuation_view: str = ""      # expensive / fair / cheap and why
    time_horizon: str = ""        # "short" / "medium" / "long"
    conviction: str = ""          # "low" / "medium" / "high"
    tags: str = ""

    def save(self) -> int:
        """Persist this thesis as a ResearchNote."""
        content_parts = []
        if self.catalysts:
            content_parts.append(f"Catalysts: {self.catalysts}")
        if self.valuation_view:
            content_parts.append(f"Valuation: {self.valuation_view}")
        if self.time_horizon:
            content_parts.append(f"Horizon: {self.time_horizon}")
        if self.conviction:
            content_parts.append(f"Conviction: {self.conviction}")

        tag_list = self.tags
        if self.conviction:
            tag_list = f"{tag_list},conviction-{self.conviction}" if tag_list else f"conviction-{self.conviction}"

        return create_note(
            title=self.title,
            symbol=self.symbol,
            content="\n".join(content_parts),
            investment_thesis=self.core_argument,
            bull_case=self.bullish_reasons,
            bear_case=self.bearish_reasons,
            risk=self.key_risks,
            tags=tag_list,
        )
