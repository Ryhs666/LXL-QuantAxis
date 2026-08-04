"""Compatibility bridge from the legacy AI page to the V2 research service."""

from datetime import date, datetime

from src.lxl_quantaxis.research import EquityResearchService, ResearchPackage
from src.lxl_quantaxis.research.reports import render_markdown


class AIEquityResearchAssistant:
    """Keep the legacy UI thin while research logic lives in the V2 application layer."""

    def __init__(self, service: EquityResearchService):
        self.service = service

    def research(self, symbol: str, *, as_of: date, generated_at: datetime) -> ResearchPackage:
        return self.service.build(symbol=symbol, as_of=as_of, generated_at=generated_at)

    def report(self, symbol: str, *, as_of: date, generated_at: datetime) -> str:
        return render_markdown(self.research(symbol, as_of=as_of, generated_at=generated_at))
