"""Immutable domain models for the Investment Memory System.

A single MemoryEntry dataclass serves four memory types via the entry_type
discriminator field. This keeps the data model simple while allowing
type-specific fields for thesis conviction, decision details, etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── Type constants ───────────────────────────────────────────

ENTRY_TYPES: tuple[str, ...] = ("note", "thesis", "decision", "reflection")

ENTRY_TYPE_LABELS: dict[str, str] = {
    "note":       "📝 研究笔记",
    "thesis":     "💡 投资论文",
    "decision":   "📊 决策记录",
    "reflection": "🧠 反思笔记",
}

OUTCOME_THESIS: tuple[str, ...] = ("pending", "correct", "wrong", "expired", "partial")
OUTCOME_DECISION: tuple[str, ...] = ("pending", "good", "bad", "neutral")

DECISION_TYPES: tuple[str, ...] = ("buy", "sell", "hold", "add", "reduce")
MOODS: tuple[str, ...] = ("calm", "excited", "anxious", "fearful", "confident", "uncertain")


# ── Data model ────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """Unified memory entry — one model for all four memory types.

    The entry_type field determines which optional fields are meaningful:
      - note:       Only base fields (title, content, symbols, tags).
      - thesis:     thesis_conviction, thesis_catalysts, thesis_risks,
                    thesis_timeline, target_price, pipeline_snapshot,
                    report_path, outcome_status.
      - decision:   decision_type, decision_price, decision_quantity,
                    decision_reason, market_context, mood, outcome_status.
      - reflection: related_ids (links to thesis/decision being reflected on).

    All fields use simple Python types to keep serialization straightforward.
    JSON fields (symbols, tags, related_ids, thesis_catalysts, thesis_risks)
    are stored as lists in Python and serialized to JSON strings in SQLite.
    """

    # ── Primary key (0 means "not yet persisted") ──
    entry_id: int = 0

    # ── Core classification ──
    entry_type: str = "note"   # note | thesis | decision | reflection
    date: str = ""             # ISO date "2026-08-06"
    title: str = ""            # Required, non-empty
    content: str = ""          # Required, Markdown body

    # ── Associations (list[str], stored as JSON arrays) ──
    symbols: list[str] = field(default_factory=list)     # e.g. ["000858"]
    tags: list[str] = field(default_factory=list)        # e.g. ["消费", "白酒"]
    project_id: str | None = None                        # FK → research_projects (Phase 3)
    related_ids: list[int] = field(default_factory=list) # FK → memory_entries.entry_id

    # ── Thesis-specific fields ──
    thesis_conviction: float | None = None       # 0.0 - 1.0
    thesis_catalysts: list[str] | None = None    # e.g. ["消费旺季", "估值修复"]
    thesis_risks: list[str] | None = None        # e.g. ["政策风险", "竞争加剧"]
    thesis_timeline: str | None = None           # "3个月" | "6个月" | "12个月"
    target_price: float | None = None            # Target price in yuan
    pipeline_snapshot: dict | None = None        # Full 7-stage pipeline output (JSON)
    report_path: str | None = None               # Path to generated report file

    # ── Decision-specific fields ──
    decision_type: str | None = None      # buy | sell | hold | add | reduce
    decision_price: float | None = None   # Execution price
    decision_quantity: float | None = None # Number of shares
    decision_reason: str | None = None    # Free-text rationale
    market_context: str | None = None     # Market environment at decision time
    mood: str | None = None               # calm | excited | anxious | fearful | confident | uncertain

    # ── Outcome tracking ──
    outcome_status: str | None = None     # pending | correct | wrong | expired | partial | good | bad | neutral
    outcome_detail: str | None = None     # Detailed review notes (Markdown)
    outcome_return: float | None = None   # Realized return (%)
    reviewed_at: str | None = None        # ISO datetime when reviewed

    # ── Metadata ──
    created_at: str = ""   # Set by database trigger
    updated_at: str = ""   # Set by application on update


# ── Validation helpers ───────────────────────────────────────

def validate_entry_type(value: str) -> str:
    """Validate and normalize entry_type."""
    if value not in ENTRY_TYPES:
        raise ValueError(f"entry_type must be one of {ENTRY_TYPES}, got {value!r}")
    return value


def validate_conviction(value: float | None) -> float | None:
    """Validate thesis_conviction is in [0.0, 1.0]."""
    if value is not None and not (0.0 <= value <= 1.0):
        raise ValueError(f"thesis_conviction must be between 0.0 and 1.0, got {value}")
    return value


def validate_required_str(value: str, field_name: str) -> str:
    """Validate a required string field is non-empty."""
    if not value or not value.strip():
        raise ValueError(f"{field_name} is required and must be non-empty")
    return value.strip()
