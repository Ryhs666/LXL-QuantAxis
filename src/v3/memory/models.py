"""Immutable domain models for the Investment Memory System.

A single MemoryEntry dataclass covers all four memory types via the `type`
discriminator.  Thesis and decision details live in structured JSON blobs
rather than dozens of sparse columns — keeping the schema simple while
preserving all domain information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Type constants ───────────────────────────────────────────

ENTRY_TYPES: tuple[str, ...] = ("note", "thesis", "decision", "reflection")

ENTRY_TYPE_LABELS: dict[str, str] = {
    "note":       "📝 研究笔记",
    "thesis":     "💡 投资论文",
    "decision":   "📊 决策记录",
    "reflection": "🧠 反思笔记",
}

TYPE_STATUSES: dict[str, tuple[str, ...]] = {
    "thesis":    ("pending", "correct", "wrong", "expired", "partial"),
    "decision":  ("pending", "good", "bad", "neutral"),
}

DECISION_TYPES: tuple[str, ...] = ("buy", "sell", "hold", "add", "reduce")
MOODS: tuple[str, ...] = ("calm", "excited", "anxious", "fearful", "confident", "uncertain")


# ── Data model ────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """Unified memory entry — one model for all four entry types.

    Schema (maps 1:1 to memory_entries table columns):
      id         — auto-increment PK (0 = not yet persisted)
      type       — note | thesis | decision | reflection
      ticker     — JSON array of stock codes, e.g. ["000858"]
      title      — required, short summary
      content    — required, Markdown body
      thesis     — JSON blob (thesis-specific fields)
      decision   — JSON blob (decision-specific fields)
      confidence — 0.0 to 1.0, top-level for easy filtering
      status     — pending | correct | wrong | expired | partial
      outcome    — JSON blob (outcome tracking fields)
      tags       — JSON array of tags
      created_at — DB default (datetime)
      updated_at — set by application on update
    """

    # ── Primary key ──
    id: int = 0

    # ── Core fields ──
    type: str = "note"
    ticker: list[str] = field(default_factory=list)     # e.g. ["000858"]
    title: str = ""
    content: str = ""                                    # Markdown

    # ── Structured sub-objects ──
    thesis: dict[str, Any] | None = None
    # {
    #   "catalysts": [...],
    #   "risks": [...],
    #   "timeline": "6 months",
    #   "target_price": 180.0,
    #   "pipeline_snapshot": {...},
    #   "report_path": "..."
    # }

    decision: dict[str, Any] | None = None
    # {
    #   "type": "buy",
    #   "price": 145.0,
    #   "quantity": 1000,
    #   "reason": "...",
    #   "market_context": "...",
    #   "mood": "confident"
    # }

    # ── Top-level for easy querying ──
    confidence: float | None = None    # 0.0 - 1.0

    # ── Outcome tracking ──
    status: str | None = None          # pending | correct | wrong | expired | partial
    outcome: dict[str, Any] | None = None
    # {
    #   "detail": "...",
    #   "return_pct": 22.0,
    #   "reviewed_at": "2026-11-20 15:30:00"
    # }

    # ── Associations ──
    tags: list[str] = field(default_factory=list)

    # ── FTS-optimized search text (auto-generated) ──
    search_text: str = ""

    # ── Metadata ──
    created_at: str = ""
    updated_at: str = ""


# ── Validation ────────────────────────────────────────────────

def validate_type(value: str) -> str:
    """Validate and normalize entry type."""
    if value not in ENTRY_TYPES:
        raise ValueError(f"type must be one of {ENTRY_TYPES}, got {value!r}")
    return value


def validate_confidence(value: float | None) -> float | None:
    """Validate confidence is in [0.0, 1.0]."""
    if value is not None and not (0.0 <= value <= 1.0):
        raise ValueError(f"confidence must be 0.0-1.0, got {value}")
    return value


def validate_required(value: str, field_name: str) -> str:
    """Validate a required string is non-empty."""
    if not value or not value.strip():
        raise ValueError(f"{field_name} is required and must be non-empty")
    return value.strip()
