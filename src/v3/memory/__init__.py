"""Investment Memory System — Phase 1 core module.

The Memory System is the persistent consciousness of LXL·QuantAxis V3.
It records every thesis, decision, observation, and lesson — and tracks
how predictions performed against reality.

Four memory types (single table, type discriminator):
  - note:       Research notes (free-form Markdown)
  - thesis:     Investment theses (structured, verifiable, trackable)
  - decision:   Trade decisions (entry/exit, rationale, market context)
  - reflection: Lessons learned (pattern recognition, rule evolution)

Public API:
  - MemoryEntry:      Immutable dataclass for all memory types
  - MemoryConfig:     Configuration (DB path, defaults)
  - MemoryDatabase:   SQLite connection + schema management
  - MemoryRepository: CRUD + FTS5 search
  - MemorySearch:     Advanced search with multi-filter support
  - MemoryAnalytics:  Aggregate statistics + confidence calibration
"""

from __future__ import annotations

from src.v3.memory.analytics import MemoryAnalytics
from src.v3.memory.config import MemoryConfig
from src.v3.memory.database import MemoryDatabase
from src.v3.memory.models import ENTRY_TYPE_LABELS, ENTRY_TYPES, MemoryEntry
from src.v3.memory.repository import MemoryRepository
from src.v3.memory.search import MemorySearch, SearchFilters, find_similar

__all__ = [
    "ENTRY_TYPES",
    "ENTRY_TYPE_LABELS",
    "MemoryAnalytics",
    "MemoryConfig",
    "MemoryDatabase",
    "MemoryEntry",
    "MemoryRepository",
    "MemorySearch",
    "SearchFilters",
    "find_similar",
]
