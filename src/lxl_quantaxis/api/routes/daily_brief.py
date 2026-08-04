"""Thin daily-brief application route."""

from dataclasses import dataclass

from src.lxl_quantaxis.ai.analyst_agent import DailyContext
from src.lxl_quantaxis.ai.orchestration import DailyAnalystOrchestrator, DailyBrief


@dataclass(frozen=True, slots=True)
class DailyBriefRoutes:
    orchestrator: DailyAnalystOrchestrator

    def get(self, context: DailyContext) -> DailyBrief:
        return self.orchestrator.run(context)
