"""Constrained note extraction with mandatory human confirmation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum

from src.lxl_quantaxis.ai.guardrails import StrategySchemaError, validate_strategy_payload
from src.lxl_quantaxis.ai.ports import LLMPort
from src.lxl_quantaxis.ai.prompts.alpha_memory import PROMPT_VERSION, build_extraction_prompt
from src.lxl_quantaxis.memory import ResearchNote


class DraftStatus(StrEnum):
    NEEDS_CONFIRMATION = "needs_confirmation"
    CONFIRMED = "confirmed"


@dataclass(frozen=True, slots=True)
class ExtractionAudit:
    prompt_version: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: str


@dataclass(frozen=True, slots=True)
class StrategyDraft:
    note: ResearchNote
    payload: Mapping[str, object] | None
    status: DraftStatus
    audit: ExtractionAudit | None
    error: str | None = None


class ConstrainedExtractionService:
    def __init__(self, llm: LLMPort) -> None:
        self.llm = llm

    def extract(self, note: ResearchNote) -> StrategyDraft:
        try:
            response = self.llm.complete(prompt=build_extraction_prompt(note.body))
            payload = json.loads(response.content)
            validated = validate_strategy_payload(payload, note=note.body)
        except (json.JSONDecodeError, StrategySchemaError, RuntimeError, TimeoutError) as error:
            return StrategyDraft(note, None, DraftStatus.NEEDS_CONFIRMATION, None, str(error))
        return StrategyDraft(
            note,
            validated,
            DraftStatus.NEEDS_CONFIRMATION,
            ExtractionAudit(
                PROMPT_VERSION,
                response.model,
                response.input_tokens,
                response.output_tokens,
                str(response.cost),
            ),
        )

    def confirm(self, draft: StrategyDraft, *, corrected_payload: object | None = None) -> StrategyDraft:
        candidate = corrected_payload if corrected_payload is not None else draft.payload
        if candidate is None:
            raise StrategySchemaError("manual draft requires a complete strategy payload")
        validated = validate_strategy_payload(candidate, note=draft.note.body)
        return replace(draft, payload=validated, status=DraftStatus.CONFIRMED, error=None)
