"""SQLite repository for the Investment Memory System.

Thin data-access layer over MemoryDatabase.  All SQL uses parameterized
queries.  JSON fields are serialized/deserialized transparently.

CJK full-text search is enabled via application-level tokenization:
Chinese characters are space-separated before storage in the search_text
column, which the FTS5 unicode61 tokenizer then indexes correctly.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from src.v3.memory.config import MemoryConfig
from src.v3.memory.database import MemoryDatabase
from src.v3.memory.models import (
    MemoryEntry,
    validate_confidence,
    validate_required,
    validate_type,
)

# ── CJK Unicode ranges ───────────────────────────────────────

_CJK_RE = re.compile(r"([一-鿿㐀-䶿豈-﫿])")


def _tokenize_cjk(text: str) -> str:
    """Insert spaces around CJK characters so FTS5 unicode61 can index them.

    "白酒行业" → " 白 酒 行 业 " (each CJK char becomes a separate token)
    "AAPL 上涨" → "AAPL  上 涨 " (English words preserved, CJK split)
    """
    return _CJK_RE.sub(r" \1 ", text)


def _make_search_text(
    title: str,
    content: str,
    tags: list[str],
    ticker: list[str],
) -> str:
    """Build the FTS-optimized search_text blob.

    Combines title + content + flattened tags + ticker codes,
    with CJK characters space-separated for unicode61 indexing.
    """
    parts: list[str] = []

    # Title and content: CJK-tokenized
    if title.strip():
        parts.append(_tokenize_cjk(title.strip()))
    if content.strip():
        # Strip Markdown syntax for cleaner search indexing
        clean = re.sub(r"[#*`>\[\]()!_~|-]", " ", content)
        parts.append(_tokenize_cjk(clean))

    # Tags: already space-separated in JSON, strip brackets and quotes
    if tags:
        parts.append(" ".join(tags))

    # Ticker codes: raw, no CJK tokenization needed
    if ticker:
        parts.append(" ".join(ticker))

    return " ".join(parts)


# ── JSON helpers ──────────────────────────────────────────────

def _to_json(value: Any) -> str:
    """Serialize a Python value to a compact JSON string."""
    if value is None:
        return "null"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _from_json(raw: str | None, default: Any = None) -> Any:
    """Deserialize a JSON string from SQLite safely."""
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


# ── Row ↔ Entry conversion ────────────────────────────────────

def _row_to_entry(row: dict) -> MemoryEntry:
    """Convert a sqlite3.Row (or dict) to a MemoryEntry."""
    return MemoryEntry(
        id=row["id"],
        type=row["type"],
        ticker=_from_json(row["ticker"], []),
        title=row["title"],
        content=row["content"],
        thesis=_from_json(row["thesis"], None),
        decision=_from_json(row["decision"], None),
        confidence=row["confidence"],
        status=row["status"],
        outcome=_from_json(row["outcome"], None),
        tags=_from_json(row["tags"], []),
        search_text=row["search_text"] or "",
        created_at=row["created_at"],
        updated_at=row["updated_at"] or "",
    )


def _entry_to_params(entry: MemoryEntry) -> dict[str, Any]:
    """Convert a MemoryEntry to a parameter dict for SQL INSERT/UPDATE."""
    search_text = entry.search_text or _make_search_text(
        entry.title, entry.content, entry.tags, entry.ticker
    )
    return {
        "type": validate_type(entry.type),
        "ticker": _to_json(entry.ticker),
        "title": validate_required(entry.title, "title"),
        "content": validate_required(entry.content, "content"),
        "search_text": search_text,
        "thesis": _to_json(entry.thesis),
        "decision": _to_json(entry.decision),
        "confidence": validate_confidence(entry.confidence),
        "status": entry.status,
        "outcome": _to_json(entry.outcome),
        "tags": _to_json(entry.tags),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ── SQL ───────────────────────────────────────────────────────

INSERT_SQL = """
INSERT INTO memory_entries (type, ticker, title, content, search_text,
                            thesis, decision, confidence, status,
                            outcome, tags, updated_at)
VALUES (:type, :ticker, :title, :content, :search_text,
        :thesis, :decision, :confidence, :status,
        :outcome, :tags, :updated_at);
"""

SELECT_BY_ID = "SELECT * FROM memory_entries WHERE id = ?;"

SELECT_ALL = """
SELECT * FROM memory_entries
ORDER BY created_at DESC, id DESC
LIMIT :limit OFFSET :offset;
"""

SELECT_BY_TYPE = """
SELECT * FROM memory_entries
WHERE type = :type
ORDER BY created_at DESC, id DESC
LIMIT :limit OFFSET :offset;
"""

COUNT_ALL = "SELECT COUNT(*) FROM memory_entries;"
COUNT_BY_TYPE = "SELECT COUNT(*) FROM memory_entries WHERE type = ?;"

UPDATE_SQL = """
UPDATE memory_entries SET
    type = :type,
    ticker = :ticker,
    title = :title,
    content = :content,
    search_text = :search_text,
    thesis = :thesis,
    decision = :decision,
    confidence = :confidence,
    status = :status,
    outcome = :outcome,
    tags = :tags,
    updated_at = :updated_at
WHERE id = :id;
"""

DELETE_SQL = "DELETE FROM memory_entries WHERE id = ?;"


# ── Repository ────────────────────────────────────────────────

class MemoryRepository:
    """CRUD repository for memory_entries.

    Delegates connection management and FTS search to MemoryDatabase.
    Handles data marshalling between MemoryEntry dataclass and SQLite rows.
    """

    def __init__(self, config: MemoryConfig | None = None) -> None:
        self._db = MemoryDatabase(config)

    @property
    def db_path(self) -> str:
        return self._db.db_path

    # ── Lifecycle ──────────────────────────────────────────

    def initialize(self) -> None:
        """Create tables and indexes. Idempotent."""
        self._db.initialize()

    @property
    def is_initialized(self) -> bool:
        return self._db.is_initialized()

    # ── CRUD ───────────────────────────────────────────────

    def save(self, entry: MemoryEntry) -> int:
        """Persist a new entry. Returns the assigned id."""
        params = _entry_to_params(entry)
        with self._db.connection() as conn:
            cursor = conn.execute(INSERT_SQL, params)
            return cursor.lastrowid

    def get_by_id(self, entry_id: int) -> MemoryEntry | None:
        """Retrieve a single entry by primary key."""
        with self._db.connection() as conn:
            row = conn.execute(SELECT_BY_ID, (entry_id,)).fetchone()
        return _row_to_entry(row) if row is not None else None

    def list_all(
        self,
        *,
        entry_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MemoryEntry]:
        """List entries, optionally filtered by type. Paginated."""
        if entry_type is not None:
            validate_type(entry_type)
            with self._db.connection() as conn:
                rows = conn.execute(
                    SELECT_BY_TYPE,
                    {"type": entry_type, "limit": limit, "offset": offset},
                ).fetchall()
        else:
            with self._db.connection() as conn:
                rows = conn.execute(
                    SELECT_ALL, {"limit": limit, "offset": offset}
                ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def count(self, *, entry_type: str | None = None) -> int:
        """Count total entries, optionally filtered by type."""
        if entry_type is not None:
            validate_type(entry_type)
            with self._db.connection() as conn:
                row = conn.execute(COUNT_BY_TYPE, (entry_type,)).fetchone()
        else:
            with self._db.connection() as conn:
                row = conn.execute(COUNT_ALL).fetchone()
        return row[0] if row else 0

    def update(self, entry_id: int, entry: MemoryEntry) -> bool:
        """Update an existing entry. Returns True if a row was updated."""
        params = _entry_to_params(entry)
        params["id"] = entry_id
        with self._db.connection() as conn:
            cursor = conn.execute(UPDATE_SQL, params)
            return cursor.rowcount > 0

    def delete(self, entry_id: int) -> bool:
        """Delete an entry by ID. Returns True if a row was deleted."""
        with self._db.connection() as conn:
            cursor = conn.execute(DELETE_SQL, (entry_id,))
            return cursor.rowcount > 0

    # ── Batch ──────────────────────────────────────────────

    def save_many(self, entries: list[MemoryEntry]) -> list[int]:
        """Persist multiple entries in a single transaction."""
        ids: list[int] = []
        with self._db.connection() as conn:
            for entry in entries:
                params = _entry_to_params(entry)
                cursor = conn.execute(INSERT_SQL, params)
                ids.append(cursor.lastrowid)
        return ids

    # ── FTS5 search ────────────────────────────────────────

    def search(
        self,
        query: str,
        *,
        entry_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MemoryEntry]:
        """Full-text search via FTS5.

        Query preprocessing:
          CJK characters are space-separated to match the tokenization
          applied during storage.  "茅台" becomes "茅 台" so it matches
          the FTS5 index where each CJK char is a separate token.

          English words are left intact: "consumer recovery" stays as-is.

        Args:
            query: Natural language search string.
                   "白酒"      → auto-tokenized to " 白  酒 "
                   "消费 白酒" → already space-separated, AND logic
                   "AAPL"      → left intact
            entry_type: Optional type filter.
            limit: Max results.
            offset: Pagination offset.
        """
        # Tokenize CJK in the query to match storage tokenization
        tokenized = _tokenize_cjk(query).strip()
        rows = self._db.fts_search(
            tokenized, entry_type=entry_type, limit=limit, offset=offset
        )
        return [_row_to_entry(r) for r in rows]

    # ── Maintenance ────────────────────────────────────────

    def rebuild_fts(self) -> None:
        """Rebuild the FTS5 index from scratch."""
        self._db.rebuild_fts()

    def optimize(self) -> None:
        """Optimize FTS5 index for faster queries."""
        self._db.optimize()
