"""Advanced Memory Search — multi-filter query engine.

Builds on MemoryRepository.search() to add ticker filter, date range,
confidence range, status filter, and related-memory discovery.
All queries are parameterized — no SQL injection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.v3.memory.database import MemoryDatabase
from src.v3.memory.models import MemoryEntry, validate_type
from src.v3.memory.repository import _from_json, _row_to_entry, _tokenize_cjk

# ── Query model ───────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class SearchFilters:
    """Immutable bag of optional search filters. All None means 'no filter'."""

    keyword: str | None = None
    entry_type: str | None = None       # note | thesis | decision | reflection
    ticker: str | None = None           # e.g. "000858"
    tags: list[str] | None = None       # e.g. ["消费"]
    date_from: str | None = None        # ISO "2026-01-01"
    date_to: str | None = None          # ISO "2026-12-31"
    confidence_min: float | None = None # 0.0 to 1.0
    confidence_max: float | None = None
    status: str | None = None           # pending | correct | wrong | ...

    limit: int = 50
    offset: int = 0

    def __post_init__(self) -> None:
        if self.entry_type is not None:
            validate_type(self.entry_type)
        if self.limit < 1:
            raise ValueError("limit must be >= 1")
        if self.offset < 0:
            raise ValueError("offset must be >= 0")


# ── Search engine ─────────────────────────────────────────────

class MemorySearch:
    """Advanced search over memory_entries with combined filters.

    Usage:
        searcher = MemorySearch(repo)
        results = searcher.query(SearchFilters(
            keyword="白酒", entry_type="thesis", ticker="000858",
        ))
        related = searcher.find_related(ticker="000858")
    """

    def __init__(self, db: MemoryDatabase) -> None:
        self._db = db

    # ── Unified query ──────────────────────────────────────

    def query(self, filters: SearchFilters) -> list[MemoryEntry]:
        """Execute a combined filter search.

        When `keyword` is provided, uses FTS5 for full-text search and
        applies additional filters as SQL WHERE clauses on the join result.
        When `keyword` is None, uses direct SQL with WHERE clauses.

        Returns results sorted by created_at DESC (newest first).
        """
        if filters.keyword and filters.keyword.strip():
            return self._fts_query(filters)
        return self._direct_query(filters)

    def count(self, filters: SearchFilters) -> int:
        """Count results matching filters (without limit/offset)."""
        if filters.keyword and filters.keyword.strip():
            return self._fts_count(filters)
        return self._direct_count(filters)

    # ── Related memory ─────────────────────────────────────

    def find_related(
        self,
        *,
        ticker: str | None = None,
        entry_id: int | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        """Find memories related to a ticker, entry, or tag set.

        At least one of ticker, entry_id, or tags must be provided.
        Excludes the seed entry (entry_id) from results.
        """
        if not ticker and entry_id is None and not tags:
            raise ValueError("At least one of ticker, entry_id, or tags is required")

        conditions: list[str] = []
        params: dict[str, Any] = {"limit": limit}

        if ticker:
            # Match ticker JSON array with LIKE (SQLite JSON support)
            conditions.append("ticker LIKE :ticker_pattern")
            params["ticker_pattern"] = f'%{ticker}%'

        if tags:
            tag_conditions: list[str] = []
            for i, tag in enumerate(tags):
                key = f"tag_{i}"
                tag_conditions.append(f"tags LIKE :{key}")
                params[key] = f'%{tag}%'
            if tag_conditions:
                conditions.append("(" + " OR ".join(tag_conditions) + ")")

        if entry_id is not None:
            conditions.append("id != :exclude_id")
            params["exclude_id"] = entry_id

            # Also find entries with same ticker as the seed entry
            with self._db.connection() as conn:
                seed = conn.execute(
                    "SELECT ticker, tags FROM memory_entries WHERE id = ?",
                    (entry_id,),
                ).fetchone()
            if seed:
                seed_tickers = _from_json(seed["ticker"], [])
                if seed_tickers:
                    # Add ticker-based matching
                    ticker_conds: list[str] = []
                    for i, t in enumerate(seed_tickers):
                        key = f"st_{i}"
                        ticker_conds.append(f"ticker LIKE :{key}")
                        params[key] = f'%{t}%'
                    conditions.append("(" + " OR ".join(ticker_conds) + ")")

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        sql = (
            f"SELECT * FROM memory_entries {where} "
            "ORDER BY created_at DESC LIMIT :limit"
        )

        with self._db.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_entry(r) for r in rows]

    # ── Convenience methods ────────────────────────────────

    def search_by_ticker(self, ticker: str, **kwargs: Any) -> list[MemoryEntry]:
        """Shortcut: find all memories for a stock code."""
        return self.query(SearchFilters(ticker=ticker, **kwargs))

    def search_by_type(self, entry_type: str, **kwargs: Any) -> list[MemoryEntry]:
        """Shortcut: find all memories of a given type."""
        return self.query(SearchFilters(entry_type=entry_type, **kwargs))

    def search_pending_reviews(self) -> list[MemoryEntry]:
        """Shortcut: find all thesis entries awaiting review."""
        return self.query(SearchFilters(
            entry_type="thesis", status="pending",
        ))

    def search_high_confidence(
        self, min_confidence: float = 0.7, **kwargs: Any
    ) -> list[MemoryEntry]:
        """Shortcut: find high-confidence thesis entries."""
        return self.query(SearchFilters(
            entry_type="thesis", confidence_min=min_confidence, **kwargs,
        ))

    # ── Internal: FTS5-based query ─────────────────────────

    def _fts_query(self, filters: SearchFilters) -> list[MemoryEntry]:
        """FTS5 full-text search with additional SQL filters."""
        tokenized = _tokenize_cjk(filters.keyword or "").strip()
        if not tokenized:
            return self._direct_query(filters)

        conditions = ["memory_entries_fts MATCH :query"]
        params: dict[str, Any] = {
            "query": tokenized,
            "limit": filters.limit,
            "offset": filters.offset,
        }
        self._add_filter_clauses(conditions, params, filters)

        where = " AND ".join(conditions)
        sql = (
            "SELECT me.* FROM memory_entries me "
            "JOIN memory_entries_fts fts ON me.id = fts.rowid "
            f"WHERE {where} "
            "ORDER BY rank "
            "LIMIT :limit OFFSET :offset"
        )

        with self._db.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_entry(r) for r in rows]

    def _fts_count(self, filters: SearchFilters) -> int:
        """Count FTS5 search results."""
        tokenized = _tokenize_cjk(filters.keyword or "").strip()
        if not tokenized:
            return self._direct_count(filters)

        conditions = ["memory_entries_fts MATCH :query"]
        params: dict[str, Any] = {"query": tokenized}
        self._add_filter_clauses(conditions, params, filters)

        where = " AND ".join(conditions)
        sql = (
            "SELECT COUNT(*) FROM memory_entries me "
            "JOIN memory_entries_fts fts ON me.id = fts.rowid "
            f"WHERE {where}"
        )

        with self._db.connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return row[0] if row else 0

    # ── Internal: direct SQL query ─────────────────────────

    def _direct_query(self, filters: SearchFilters) -> list[MemoryEntry]:
        """Direct SQL query without FTS5 (no keyword)."""
        conditions: list[str] = []
        params: dict[str, Any] = {
            "limit": filters.limit,
            "offset": filters.offset,
        }
        self._add_filter_clauses(conditions, params, filters)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = (
            "SELECT * FROM memory_entries AS me "
            f"{where} "
            "ORDER BY created_at DESC "
            "LIMIT :limit OFFSET :offset"
        )

        with self._db.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_entry(r) for r in rows]

    def _direct_count(self, filters: SearchFilters) -> int:
        """Direct SQL count without FTS5."""
        conditions: list[str] = []
        params: dict[str, Any] = {}
        self._add_filter_clauses(conditions, params, filters)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"SELECT COUNT(*) FROM memory_entries AS me {where}"

        with self._db.connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return row[0] if row else 0

    # ── Internal: shared filter SQL builder ────────────────

    @staticmethod
    def _add_filter_clauses(
        conditions: list[str],
        params: dict[str, Any],
        filters: SearchFilters,
    ) -> None:
        """Append WHERE clauses and parameters for non-keyword filters."""
        if filters.entry_type is not None:
            conditions.append("me.type = :filter_type")
            params["filter_type"] = filters.entry_type

        if filters.ticker is not None:
            conditions.append("me.ticker LIKE :filter_ticker")
            params["filter_ticker"] = f"%{filters.ticker}%"

        if filters.tags:
            for i, tag in enumerate(filters.tags):
                key = f"filter_tag_{i}"
                conditions.append(f"me.tags LIKE :{key}")
                params[key] = f"%{tag}%"

        if filters.date_from is not None:
            conditions.append("me.created_at >= :filter_date_from")
            params["filter_date_from"] = filters.date_from

        if filters.date_to is not None:
            conditions.append("me.created_at <= :filter_date_to")
            params["filter_date_to"] = filters.date_to + " 23:59:59"

        if filters.confidence_min is not None:
            conditions.append("me.confidence >= :filter_conf_min")
            params["filter_conf_min"] = filters.confidence_min

        if filters.confidence_max is not None:
            conditions.append("me.confidence <= :filter_conf_max")
            params["filter_conf_max"] = filters.confidence_max

        if filters.status is not None:
            conditions.append("me.status = :filter_status")
            params["filter_status"] = filters.status


# ── Standalone helpers ────────────────────────────────────────

def find_similar(
    db: MemoryDatabase,
    entry_id: int,
    limit: int = 10,
) -> list[MemoryEntry]:
    """Find entries similar to a given entry by tag and ticker overlap.

    Pure function — uses no AI, just SQL LIKE matching on tags and tickers.
    Useful for discovering related research without a vector database.
    """
    # Get the seed entry
    with db.connection() as conn:
        seed = conn.execute(
            "SELECT ticker, tags FROM memory_entries WHERE id = ?",
            (entry_id,),
        ).fetchone()

    if seed is None:
        return []

    tickers = _from_json(seed["ticker"], [])
    tags = _from_json(seed["tags"], [])

    # Build a scored similarity query
    conditions: list[str] = ["id != :exclude_id"]
    params: dict[str, Any] = {"exclude_id": entry_id, "limit": limit}

    for i, t in enumerate(tickers):
        key = f"t_{i}"
        conditions.append(f"(CASE WHEN ticker LIKE :{key} THEN 2 ELSE 0 END)")
        params[key] = f"%{t}%"

    for i, tag in enumerate(tags):
        key = f"g_{i}"
        conditions.append(f"(CASE WHEN tags LIKE :{key} THEN 1 ELSE 0 END)")
        params[key] = f"%{tag}%"

    score_expr = " + ".join(conditions[1:])  # skip 'id !='
    sql = (
        f"SELECT *, ({score_expr}) AS similarity FROM memory_entries "
        "WHERE id != :exclude_id "
        "ORDER BY similarity DESC "
        "LIMIT :limit"
    )

    with db.connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    # Filter out zero-similarity results
    return [
        _row_to_entry(r) for r in rows
        if r["similarity"] > 0
    ]
