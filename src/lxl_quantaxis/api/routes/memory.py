"""Framework-neutral memory route handlers."""

from dataclasses import dataclass

from src.lxl_quantaxis.memory import ResearchNote
from src.lxl_quantaxis.memory.extraction import ConstrainedExtractionService, StrategyDraft


@dataclass(frozen=True, slots=True)
class MemoryRoutes:
    extraction: ConstrainedExtractionService

    def create_draft(self, note: ResearchNote) -> StrategyDraft:
        return self.extraction.extract(note)

    def confirm_draft(self, draft: StrategyDraft, corrected_payload: object | None = None) -> StrategyDraft:
        return self.extraction.confirm(draft, corrected_payload=corrected_payload)
