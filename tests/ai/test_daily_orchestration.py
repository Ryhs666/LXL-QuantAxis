from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.lxl_quantaxis.ai.analyst_agent import AgentConclusion, AgentResult, DailyContext
from src.lxl_quantaxis.ai.orchestration import BriefStatus, DailyAnalystOrchestrator
from src.lxl_quantaxis.research import Evidence

AS_OF = date(2026, 1, 5)
CONTEXT = DailyContext("org-a", AS_OF, "CSI 300 closed higher on the fixed snapshot.")


@dataclass(frozen=True)
class FixtureAgent:
    agent_id: str
    cost: Decimal = Decimal("0.10")
    failure: Exception | None = None
    cited: bool = True

    def analyze(self, context: DailyContext) -> AgentResult:
        if self.failure is not None:
            raise self.failure
        evidence = Evidence(f"{self.agent_id}-1", "fixture", "snapshot", context.data_as_of)
        ids = (evidence.evidence_id,) if self.cited else ()
        return AgentResult(
            self.agent_id,
            (AgentConclusion(f"{self.agent_id} conclusion", ids),),
            (evidence,),
            self.cost,
        )


class DailyOrchestrationTests(unittest.TestCase):
    def test_fixed_snapshot_produces_evidence_complete_brief(self) -> None:
        agents = tuple(
            FixtureAgent(name)
            for name in (
                "regime",
                "company",
                "industry",
                "news",
                "opportunity",
                "memory",
                "risk",
                "report",
            )
        )
        brief = DailyAnalystOrchestrator(agents, Decimal("1.00")).run(CONTEXT)
        self.assertIs(brief.status, BriefStatus.COMPLETE)
        self.assertEqual(len(brief.sections), 8)
        self.assertEqual(len(brief.evidence), 8)

    def test_agent_timeout_degrades_without_losing_deterministic_summary(self) -> None:
        brief = DailyAnalystOrchestrator(
            (FixtureAgent("regime"), FixtureAgent("news", failure=TimeoutError("timeout"))),
            Decimal("1"),
        ).run(CONTEXT)
        self.assertIs(brief.status, BriefStatus.DEGRADED)
        self.assertEqual(brief.fallback_summary, CONTEXT.market_summary)
        self.assertIn("news: timeout", brief.failures)

    def test_uncited_conclusion_is_rejected(self) -> None:
        brief = DailyAnalystOrchestrator((FixtureAgent("news", cited=False),), Decimal("1")).run(CONTEXT)
        self.assertEqual(brief.sections, ())
        self.assertIn("news: conclusion has no evidence", brief.failures)

    def test_cost_budget_rejects_expensive_agent(self) -> None:
        brief = DailyAnalystOrchestrator(
            (FixtureAgent("regime", Decimal("0.6")), FixtureAgent("news", Decimal("0.6"))),
            Decimal("1"),
        ).run(CONTEXT)
        self.assertEqual([name for name, _ in brief.sections], ["regime"])
        self.assertEqual(brief.total_cost, Decimal("0.6"))
        self.assertIn("news: cost budget exceeded", brief.failures)


if __name__ == "__main__":
    unittest.main()
