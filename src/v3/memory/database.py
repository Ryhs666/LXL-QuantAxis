"""SQLite database layer for the Investment Memory System.

Handles connection lifecycle, schema initialization, and FTS5 index
maintenance. All SQL is parameterized — never concatenated.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from src.v3.memory.config import MemoryConfig

_SCHEMA: str | None = None


def _load_schema() -> str:
    """Load schema.sql from disk. Cached after first read."""
    global _SCHEMA
    if _SCHEMA is None:
        schema_path = Path(__file__).parent / "schema.sql"
        _SCHEMA = schema_path.read_text(encoding="utf-8")
    return _SCHEMA


class MemoryDatabase:
    """Manages the lxl_v3.db SQLite database lifecycle.

    Responsibilities:
      - Creates the database file and parent directories
      - Runs schema.sql (idempotent via IF NOT EXISTS)
      - Provides connection context manager with WAL mode
      - Does NOT contain query logic (that's in MemoryRepository)
    """

    def __init__(self, config: MemoryConfig | None = None) -> None:
        self.config = config or MemoryConfig.with_defaults()
        self._db_path = str(self.config.db_path)

    @property
    def db_path(self) -> str:
        return self._db_path

    # ── Connection ────────────────────────────────────────────

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Get a SQLite connection with WAL mode and foreign keys enabled.

        Creates parent directories if they don't exist.
        Commits on success, rolls back on exception.
        """
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Schema management ─────────────────────────────────────

    def initialize(self) -> None:
        """Create all tables, indexes, FTS virtual tables, and triggers.

        Idempotent — safe to call multiple times. Uses IF NOT EXISTS
        throughout the schema.
        """
        schema = _load_schema()
        with self.connection() as conn:
            conn.executescript(schema)

    def is_initialized(self) -> bool:
        """Check whether the memory_entries table exists."""
        try:
            with self.connection() as conn:
                row = conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name='memory_entries';"
                ).fetchone()
                return row is not None
        except Exception:
            return False

    # ── FTS maintenance ───────────────────────────────────────

    def rebuild_fts(self) -> None:
        """Rebuild the FTS5 index from scratch.

        Useful after bulk imports or if indexes get out of sync.
        """
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO memory_entries_fts(memory_entries_fts) "
                "VALUES ('rebuild');"
            )

    def optimize(self) -> None:
        """Optimize the FTS5 index for faster queries."""
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO memory_entries_fts(memory_entries_fts) "
                "VALUES ('optimize');"
            )

    def fts_search(
        self,
        query: str,
        *,
        entry_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[sqlite3.Row]:
        """Execute a full-text search against memory_entries_fts.

        Args:
            query: FTS5 query string. Supports:
                   - "白酒"              single word
                   - "白酒 消费"         AND logic
                   - "白酒 OR 茅台"      OR logic
                   - '"消费复苏"'        exact phrase
            entry_type: Optional type filter.
            limit: Max results.
            offset: Pagination offset.

        Returns:
            Raw sqlite3.Row objects. Caller is responsible for
            converting to MemoryEntry.
        """
        if entry_type is not None:
            with self.connection() as conn:
                rows = conn.execute(
                    "SELECT me.* FROM memory_entries me "
                    "JOIN memory_entries_fts fts ON me.id = fts.rowid "
                    "WHERE memory_entries_fts MATCH ? AND me.type = ? "
                    "ORDER BY rank "
                    "LIMIT ? OFFSET ?",
                    (query, entry_type, limit, offset),
                ).fetchall()
        else:
            with self.connection() as conn:
                rows = conn.execute(
                    "SELECT me.* FROM memory_entries me "
                    "JOIN memory_entries_fts fts ON me.id = fts.rowid "
                    "WHERE memory_entries_fts MATCH ? "
                    "ORDER BY rank "
                    "LIMIT ? OFFSET ?",
                    (query, limit, offset),
                ).fetchall()
        return rows
