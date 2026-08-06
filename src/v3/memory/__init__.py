"""Investment Memory System — Phase 1 core module.

The Memory System is the persistent consciousness of LXL·QuantAxis V3.
It records every thesis, decision, observation, and lesson — and tracks
how predictions performed against reality.

Four memory types (single table, entry_type discriminator):
  - note:       Research notes (free-form Markdown)
  - thesis:     Investment theses (structured, verifiable, trackable)
  - decision:   Trade decisions (entry/exit, rationale, market context)
  - reflection: Lessons learned (pattern recognition, rule evolution)

Public API:
  - MemoryEntry:  Immutable dataclass for all memory types
  - MemoryRepository: SQLite CRUD with parameterized queries
  - MemoryConfig:  Configuration (DB path, defaults)
"""

from __future__ import annotations

from src.v3.memory.config import MemoryConfig
from src.v3.memory.models import ENTRY_TYPE_LABELS, ENTRY_TYPES, MemoryEntry
from src.v3.memory.repository import MemoryRepository

__all__ = [
    "ENTRY_TYPES",
    "ENTRY_TYPE_LABELS",
    "MemoryConfig",
    "MemoryEntry",
    "MemoryRepository",
]
