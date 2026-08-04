"""ResearchNote — immutable investment research memory."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True, slots=True)
class ResearchNote:
    """A single research observation about a security or market.

    Immutable by design — once written, a note becomes part of the
    permanent research record.  To update, create a new note and
    link to the previous version.
    """

    id: int | None = None
    date: str = ""                          # YYYY-MM-DD
    symbol: str = ""                        # security identifier
    title: str = ""
    content: str = ""                       # body / observation
    investment_thesis: str = ""             # the core argument
    bull_case: str = ""                     # upside scenario
    bear_case: str = ""                     # downside scenario
    risk: str = ""                          # key risk factors
    tags: str = ""                          # comma-separated
    created_at: str = ""                    # ISO timestamp

    def __post_init__(self) -> None:
        if not self.date:
            object.__setattr__(self, "date", datetime.now().strftime("%Y-%m-%d"))
        if not self.created_at:
            object.__setattr__(self, "created_at", datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date,
            "symbol": self.symbol,
            "title": self.title,
            "content": self.content,
            "investment_thesis": self.investment_thesis,
            "bull_case": self.bull_case,
            "bear_case": self.bear_case,
            "risk": self.risk,
            "tags": self.tags,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ResearchNote:
        return cls(
            id=d.get("id"),
            date=str(d.get("date", "")),
            symbol=str(d.get("symbol", "")),
            title=str(d.get("title", "")),
            content=str(d.get("content", "")),
            investment_thesis=str(d.get("investment_thesis", "")),
            bull_case=str(d.get("bull_case", "")),
            bear_case=str(d.get("bear_case", "")),
            risk=str(d.get("risk", "")),
            tags=str(d.get("tags", "")),
            created_at=str(d.get("created_at", "")),
        )
