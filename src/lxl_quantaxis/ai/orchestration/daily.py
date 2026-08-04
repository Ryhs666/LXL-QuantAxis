"""Fail-soft daily analyst orchestration with evidence and cost gates."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from src.lxl_quantaxis.ai.analyst_agent import AgentConclusion, AgentResult, AnalystAgent, DailyContext
from src.lxl_quantaxis.research import Evidence


class BriefStatus(StrEnum):
    COMPLETE = "complete"
    DEGRADED = "degraded"


@dataclass(frozen=True, slots=True)
class DailyBrief:
    status: BriefStatus
    data_as_of: str
    sections: tuple[tuple[str, tuple[AgentConclusion, ...]], ...]
    evidence: tuple[Evidence, ...]
    failures: tuple[str, ...]
    total_cost: Decimal
    fallback_summary: str


@dataclass(frozen=True, slots=True)
class DailyAnalystOrchestrator:
    agents: tuple[AnalystAgent, ...]
    cost_budget: Decimal

    def run(self, context: DailyContext) -> DailyBrief:
        sections: list[tuple[str, tuple[AgentConclusion, ...]]] = []
        evidence: list[Evidence] = []
        failures: list[str] = []
        total_cost = Decimal("0")
        for agent in self.agents:
            try:
                result = agent.analyze(context)
                self._validate_result(agent, result, context)
            except (RuntimeError, TimeoutError, ValueError) as error:
                failures.append(f"{agent.agent_id}: {error}")
                continue
            if total_cost + result.cost > self.cost_budget:
                failures.append(f"{agent.agent_id}: cost budget exceeded")
                continue
            total_cost += result.cost
            sections.append((result.agent_id, result.conclusions))
            evidence.extend(result.evidence)
        return DailyBrief(
            BriefStatus.DEGRADED if failures else BriefStatus.COMPLETE,
            context.data_as_of.isoformat(),
            tuple(sections),
            tuple(sorted(evidence, key=lambda item: item.evidence_id)),
            tuple(failures),
            total_cost,
            context.market_summary,
        )

    @staticmethod
    def _validate_result(agent: AnalystAgent, result: AgentResult, context: DailyContext) -> None:
        if result.agent_id != agent.agent_id:
            raise ValueError("agent identity mismatch")
        known = {item.evidence_id for item in result.evidence if item.as_of <= context.data_as_of}
        if not result.conclusions:
            raise ValueError("agent returned no conclusions")
        for conclusion in result.conclusions:
            if not conclusion.text.strip() or not conclusion.evidence_ids:
                raise ValueError("conclusion has no evidence")
            if not set(conclusion.evidence_ids) <= known:
                raise ValueError("conclusion references missing or future evidence")
