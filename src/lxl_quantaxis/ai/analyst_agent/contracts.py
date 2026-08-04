"""Contracts for evidence-producing daily analyst agents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from src.lxl_quantaxis.research import Evidence


@dataclass(frozen=True, slots=True)
class DailyContext:
    organization_id: str
    data_as_of: date
    market_summary: str


@dataclass(frozen=True, slots=True)
class AgentConclusion:
    text: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AgentResult:
    agent_id: str
    conclusions: tuple[AgentConclusion, ...]
    evidence: tuple[Evidence, ...]
    cost: Decimal = Decimal("0")


class AnalystAgent(Protocol):
    @property
    def agent_id(self) -> str: ...

    def analyze(self, context: DailyContext) -> AgentResult: ...
