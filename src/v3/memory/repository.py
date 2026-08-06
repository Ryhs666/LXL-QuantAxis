"""SQLite repository for the Investment Memory System.

Provides CRUD operations on the memory_entries table with:
  - Parameterized queries (no SQL injection)
  - JSON serialization for list/dict fields
  - Input validation before write
  - WAL mode for concurrent read safety
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from src.v3.memory.config import MemoryConfig
from src.v3.memory.models import (
    MemoryEntry,
    validate_conviction,
    validate_entry_type,
    validate_required_str,
)

# ── SQL statements ───────────────────────────────────────────

CREATE_MEMORY_ENTRIES = """
CREATE TABLE IF NOT EXISTS memory_entries (
    entry_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_type   TEXT    NOT NULL CHECK (entry_type IN (
                    'note', 'thesis', 'decision', 'reflection'
                 )),
    date         TEXT    NOT NULL,
    title        TEXT    NOT NULL,
    content      TEXT    NOT NULL,

    symbols      TEXT    NOT NULL DEFAULT '[]',
    tags         TEXT    NOT NULL DEFAULT '[]',
    project_id   TEXT,
    related_ids  TEXT    NOT NULL DEFAULT '[]',

    thesis_conviction    REAL,
    thesis_catalysts     TEXT,
    thesis_risks         TEXT,
    thesis_timeline      TEXT,
    target_price         REAL,
    pipeline_snapshot    TEXT,
    report_path          TEXT,

    decision_type        TEXT,
    decision_price       REAL,
    decision_quantity    REAL,
    decision_reason      TEXT,
    market_context       TEXT,
    mood                 TEXT,

    outcome_status       TEXT    DEFAULT 'pending',
    outcome_detail       TEXT,
    outcome_return       REAL,
    reviewed_at          TEXT,

    created_at           TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at           TEXT
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_memory_type    ON memory_entries(entry_type);",
    "CREATE INDEX IF NOT EXISTS idx_memory_date    ON memory_entries(date);",
    "CREATE INDEX IF NOT EXISTS idx_memory_outcome ON memory_entries(outcome_status);",
    "CREATE INDEX IF NOT EXISTS idx_memory_project ON memory_entries(project_id);",
    "CREATE INDEX IF NOT EXISTS idx_memory_created ON memory_entries(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_memory_symbols ON memory_entries(symbols);",
]

INSERT_SQL = """
INSERT INTO memory_entries (
    entry_type, date, title, content,
    symbols, tags, project_id, related_ids,
    thesis_conviction, thesis_catalysts, thesis_risks,
    thesis_timeline, target_price, pipeline_snapshot, report_path,
    decision_type, decision_price, decision_quantity,
    decision_reason, market_context, mood,
    outcome_status, outcome_detail, outcome_return, reviewed_at,
    updated_at
) VALUES (
    :entry_type, :date, :title, :content,
    :symbols, :tags, :project_id, :related_ids,
    :thesis_conviction, :thesis_catalysts, :thesis_risks,
    :thesis_timeline, :target_price, :pipeline_snapshot, :report_path,
    :decision_type, :decision_price, :decision_quantity,
    :decision_reason, :market_context, :mood,
    :outcome_status, :outcome_detail, :outcome_return, :reviewed_at,
    :updated_at
);
"""

SELECT_BY_ID = "SELECT * FROM memory_entries WHERE entry_id = ?;"

SELECT_ALL = """
SELECT * FROM memory_entries
ORDER BY date DESC, entry_id DESC
LIMIT :limit OFFSET :offset;
"""

SELECT_BY_TYPE = """
SELECT * FROM memory_entries
WHERE entry_type = :entry_type
ORDER BY date DESC, entry_id DESC
LIMIT :limit OFFSET :offset;
"""

COUNT_ALL = "SELECT COUNT(*) FROM memory_entries;"
COUNT_BY_TYPE = "SELECT COUNT(*) FROM memory_entries WHERE entry_type = ?;"

UPDATE_SQL = """
UPDATE memory_entries SET
    title = :title,
    content = :content,
    symbols = :symbols,
    tags = :tags,
    project_id = :project_id,
    related_ids = :related_ids,
    thesis_conviction = :thesis_conviction,
    thesis_catalysts = :thesis_catalysts,
    thesis_risks = :thesis_risks,
    thesis_timeline = :thesis_timeline,
    target_price = :target_price,
    pipeline_snapshot = :pipeline_snapshot,
    report_path = :report_path,
    decision_type = :decision_type,
    decision_price = :decision_price,
    decision_quantity = :decision_quantity,
    decision_reason = :decision_reason,
    market_context = :market_context,
    mood = :mood,
    outcome_status = :outcome_status,
    outcome_detail = :outcome_detail,
    outcome_return = :outcome_return,
    reviewed_at = :reviewed_at,
    updated_at = :updated_at
WHERE entry_id = :entry_id;
"""

DELETE_SQL = "DELETE FROM memory_entries WHERE entry_id = ?;"


# ── Helpers ──────────────────────────────────────────────────

def _to_json(value: list | dict | None) -> str:
    """Serialize a Python value to a JSON string for SQLite storage."""
    if value is None:
        return "[]" if isinstance(value, list) else "null"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _from_json(raw: str | None, default: Any = None) -> Any:
    """Deserialize a JSON string from SQLite to a Python value."""
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def _row_to_entry(row: sqlite3.Row) -> MemoryEntry:
    """Convert a sqlite3.Row to a MemoryEntry.

    JSON-serialized columns (symbols, tags, related_ids, thesis_catalysts,
    thesis_risks, pipeline_snapshot) are deserialized back to Python objects.
    """
    return MemoryEntry(
        entry_id=row["entry_id"],
        entry_type=row["entry_type"],
        date=row["date"],
        title=row["title"],
        content=row["content"],
        symbols=_from_json(row["symbols"], []),
        tags=_from_json(row["tags"], []),
        project_id=row["project_id"],
        related_ids=_from_json(row["related_ids"], []),
        thesis_conviction=row["thesis_conviction"],
        thesis_catalysts=_from_json(row["thesis_catalysts"], None),
        thesis_risks=_from_json(row["thesis_risks"], None),
        thesis_timeline=row["thesis_timeline"],
        target_price=row["target_price"],
        pipeline_snapshot=_from_json(row["pipeline_snapshot"], None),
        report_path=row["report_path"],
        decision_type=row["decision_type"],
        decision_price=row["decision_price"],
        decision_quantity=row["decision_quantity"],
        decision_reason=row["decision_reason"],
        market_context=row["market_context"],
        mood=row["mood"],
        outcome_status=row["outcome_status"],
        outcome_detail=row["outcome_detail"],
        outcome_return=row["outcome_return"],
        reviewed_at=row["reviewed_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"] or "",
    )


def _entry_to_params(entry: MemoryEntry) -> dict[str, Any]:
    """Convert a MemoryEntry to a parameter dict for SQL INSERT/UPDATE."""
    from datetime import datetime

    return {
        "entry_id": entry.entry_id,
        "entry_type": validate_entry_type(entry.entry_type),
        "date": entry.date,
        "title": validate_required_str(entry.title, "title"),
        "content": validate_required_str(entry.content, "content"),
        "symbols": _to_json(entry.symbols),
        "tags": _to_json(entry.tags),
        "project_id": entry.project_id,
        "related_ids": _to_json(entry.related_ids),
        "thesis_conviction": validate_conviction(entry.thesis_conviction),
        "thesis_catalysts": _to_json(entry.thesis_catalysts),
        "thesis_risks": _to_json(entry.thesis_risks),
        "thesis_timeline": entry.thesis_timeline,
        "target_price": entry.target_price,
        "pipeline_snapshot": _to_json(entry.pipeline_snapshot),
        "report_path": entry.report_path,
        "decision_type": entry.decision_type,
        "decision_price": entry.decision_price,
        "decision_quantity": entry.decision_quantity,
        "decision_reason": entry.decision_reason,
        "market_context": entry.market_context,
        "mood": entry.mood,
        "outcome_status": entry.outcome_status,
        "outcome_detail": entry.outcome_detail,
        "outcome_return": entry.outcome_return,
        "reviewed_at": entry.reviewed_at,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ── Repository ───────────────────────────────────────────────

class MemoryRepository:
    """SQLite repository for the Investment Memory System.

    Usage:
        config = MemoryConfig.with_defaults()
        repo = MemoryRepository(config)
        repo.initialize()            # Create tables on first run

        entry = MemoryEntry(entry_type="note", date="2026-08-06",
                           title="My note", content="...")
        entry_id = repo.save(entry)
        retrieved = repo.get_by_id(entry_id)
    """

    def __init__(self, config: MemoryConfig | None = None) -> None:
        self.config = config or MemoryConfig.with_defaults()
        self._db_path = str(self.config.db_path)

    @property
    def db_path(self) -> str:
        return self._db_path

    # ── Connection management ──────────────────────────────

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager for SQLite connections with WAL mode and foreign keys."""
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

    # ── Database initialization ────────────────────────────

    def initialize(self) -> None:
        """Create tables and indexes if they don't exist. Idempotent."""
        with self.connection() as conn:
            conn.executescript(CREATE_MEMORY_ENTRIES)
            for index_sql in CREATE_INDEXES:
                conn.execute(index_sql)

    def is_initialized(self) -> bool:
        """Check if the database has been initialized."""
        try:
            with self.connection() as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_entries';"
                )
                return cursor.fetchone() is not None
        except Exception:
            return False

    # ── CRUD operations ────────────────────────────────────

    def save(self, entry: MemoryEntry) -> int:
        """Persist a new MemoryEntry. Returns the assigned entry_id."""
        params = _entry_to_params(entry)
        del params["entry_id"]  # Let SQLite auto-increment

        with self.connection() as conn:
            cursor = conn.execute(INSERT_SQL, params)
            return cursor.lastrowid

    def get_by_id(self, entry_id: int) -> MemoryEntry | None:
        """Retrieve a single entry by primary key."""
        with self.connection() as conn:
            row = conn.execute(SELECT_BY_ID, (entry_id,)).fetchone()
        return _row_to_entry(row) if row is not None else None

    def list_all(
        self,
        *,
        entry_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MemoryEntry]:
        """List entries, optionally filtered by type. Paginated.

        Args:
            entry_type: Filter by entry type (note/thesis/decision/reflection).
            limit: Max entries to return.
            offset: Number of entries to skip.
        """
        if entry_type is not None:
            validate_entry_type(entry_type)
            with self.connection() as conn:
                rows = conn.execute(
                    SELECT_BY_TYPE,
                    {"entry_type": entry_type, "limit": limit, "offset": offset},
                ).fetchall()
        else:
            with self.connection() as conn:
                rows = conn.execute(
                    SELECT_ALL,
                    {"limit": limit, "offset": offset},
                ).fetchall()
        return [_row_to_entry(row) for row in rows]

    def count(self, *, entry_type: str | None = None) -> int:
        """Count total entries, optionally filtered by type."""
        if entry_type is not None:
            validate_entry_type(entry_type)
            with self.connection() as conn:
                row = conn.execute(COUNT_BY_TYPE, (entry_type,)).fetchone()
        else:
            with self.connection() as conn:
                row = conn.execute(COUNT_ALL).fetchone()
        return row[0] if row else 0

    def update(self, entry_id: int, entry: MemoryEntry) -> bool:
        """Update an existing entry. Returns True if a row was updated."""
        params = _entry_to_params(entry)
        params["entry_id"] = entry_id

        with self.connection() as conn:
            cursor = conn.execute(UPDATE_SQL, params)
            return cursor.rowcount > 0

    def delete(self, entry_id: int) -> bool:
        """Delete an entry by ID. Returns True if a row was deleted."""
        with self.connection() as conn:
            cursor = conn.execute(DELETE_SQL, (entry_id,))
            return cursor.rowcount > 0

    # ── Batch save ─────────────────────────────────────────

    def save_many(self, entries: list[MemoryEntry]) -> list[int]:
        """Persist multiple entries in a single transaction. Returns entry IDs."""
        ids: list[int] = []
        with self.connection() as conn:
            for entry in entries:
                params = _entry_to_params(entry)
                del params["entry_id"]
                cursor = conn.execute(INSERT_SQL, params)
                ids.append(cursor.lastrowid)
        return ids
