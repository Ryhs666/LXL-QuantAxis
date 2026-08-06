"""Workspace data adapters — zero new tables, pure read/compose layer.

MemoryAdapter:   Queries memory_entries via tag conventions.
PortfolioAdapter: Read-only access to V2 trades.db open positions.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from typing import Any

from src.v3.memory.database import MemoryDatabase
from src.v3.memory.repository import MemoryRepository
from src.v3.memory.search import MemorySearch, SearchFilters

# ═══════════════════════════════════════════════════════════════
# MemoryAdapter — tag-convention queries over memory_entries
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class WatchlistItem:
    """A single watchlist entry projected from a memory_entries row."""
    id: int
    ticker: list[str]
    title: str
    content: str
    tags: list[str]
    priority: str          # "high" | "med" | "low"
    created_at: str


@dataclass(frozen=True, slots=True)
class QueueItem:
    """A single research queue entry."""
    id: int
    ticker: list[str]
    title: str
    content: str
    tags: list[str]
    priority: str
    created_at: str


@dataclass(frozen=True, slots=True)
class ActiveThesis:
    """A pending thesis projected for workspace display."""
    id: int
    ticker: list[str]
    title: str
    content: str
    thesis: dict[str, Any] | None
    confidence: float | None
    tags: list[str]
    created_at: str


class MemoryAdapter:
    """Read/write adapter for workspace concepts stored in memory_entries.

    Tag conventions (no new tables):
      - Watchlist:  type='note',  tags CONTAINS 'watchlist'
      - Queue:      type='note',  tags CONTAINS 'queue'
      - Thesis:     type='thesis', status='pending'
    """

    def __init__(self, db: MemoryDatabase) -> None:
        self._db = db
        self._search = MemorySearch(db)

    # ── Watchlist ──────────────────────────────────────────

    def get_watchlist(self) -> list[WatchlistItem]:
        """Get all watchlist entries, ordered by priority then date."""
        entries = self._search.query(SearchFilters(
            entry_type="note", tags=["watchlist"],
        ))
        return [_to_watchlist(e) for e in entries]

    def add_to_watchlist(
        self,
        ticker: list[str],
        title: str,
        content: str = "",
        tags: list[str] | None = None,
        priority: str = "med",
    ) -> int:
        """Add a new watchlist item. Returns the new entry_id."""
        from src.v3.memory.models import MemoryEntry

        all_tags = ["watchlist", f"priority:{priority}"]
        if tags:
            all_tags.extend(tags)

        entry = MemoryEntry(
            type="note", ticker=ticker, title=title,
            content=content, tags=all_tags,
        )
        repo = MemoryRepository()
        return repo.save(entry)

    def remove_from_watchlist(self, entry_id: int) -> bool:
        """Remove a watchlist item by deleting its memory entry."""
        repo = MemoryRepository()
        return repo.delete(entry_id)

    # ── Research Queue ────────────────────────────────────

    def get_queue(self) -> list[QueueItem]:
        """Get all queue entries, ordered by priority then date."""
        entries = self._search.query(SearchFilters(
            entry_type="note", tags=["queue"],
        ))
        return [_to_queue(e) for e in entries]

    def add_to_queue(
        self,
        title: str,
        ticker: list[str] | None = None,
        content: str = "",
        tags: list[str] | None = None,
        priority: str = "med",
    ) -> int:
        """Add a new queue item. Returns the new entry_id."""
        from src.v3.memory.models import MemoryEntry

        all_tags = ["queue", f"priority:{priority}"]
        if tags:
            all_tags.extend(tags)

        entry = MemoryEntry(
            type="note", ticker=ticker or [], title=title,
            content=content, tags=all_tags,
        )
        repo = MemoryRepository()
        return repo.save(entry)

    def mark_queue_done(self, entry_id: int) -> bool:
        """Mark a queue item as done by removing the 'queue' tag."""
        repo = MemoryRepository()
        entry = repo.get_by_id(entry_id)
        if entry is None:
            return False
        new_tags = [t for t in entry.tags if t != "queue"]
        updated = type(entry)(
            id=entry.id, type=entry.type, ticker=entry.ticker,
            title=entry.title, content=entry.content,
            thesis=entry.thesis, decision=entry.decision,
            confidence=entry.confidence, status=entry.status,
            outcome=entry.outcome, tags=new_tags,
            created_at=entry.created_at,
        )
        return repo.update(entry_id, updated)

    # ── Active Thesis ─────────────────────────────────────

    def get_active_theses(self) -> list[ActiveThesis]:
        """Get all pending theses with their structured data."""
        entries = self._search.query(SearchFilters(
            entry_type="thesis", status="pending",
        ))
        return [_to_active_thesis(e) for e in entries]

    def mark_thesis_outcome(
        self, entry_id: int, status: str, detail: str, return_pct: float | None = None
    ) -> bool:
        """Mark a thesis as correct or wrong with outcome details."""
        from datetime import datetime

        repo = MemoryRepository()
        entry = repo.get_by_id(entry_id)
        if entry is None:
            return False

        outcome = {
            "detail": detail,
            "return_pct": return_pct,
            "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        updated = type(entry)(
            id=entry.id, type=entry.type, ticker=entry.ticker,
            title=entry.title, content=entry.content,
            thesis=entry.thesis, decision=entry.decision,
            confidence=entry.confidence, status=status,
            outcome=outcome, tags=entry.tags,
            created_at=entry.created_at,
        )
        return repo.update(entry_id, updated)

    # ── Pending Reviews ───────────────────────────────────

    def get_pending_reviews(self, min_age_days: int = 30) -> list[dict[str, Any]]:
        """Get thesis entries that have been pending for too long."""
        from src.v3.memory.analytics import MemoryAnalytics
        a = MemoryAnalytics(self._db)
        return a.get_pending_reviews(min_days_since_creation=min_age_days)

    def get_recent_reflections(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get recent reflection entries."""
        entries = self._search.query(SearchFilters(
            entry_type="reflection", limit=limit,
        ))
        return [
            {"id": e.id, "title": e.title, "tags": e.tags, "created_at": e.created_at}
            for e in entries
        ]


# ═══════════════════════════════════════════════════════════════
# PortfolioAdapter — read-only V2 trades.db access
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class PortfolioPosition:
    """A single open position from V2 trades.db."""
    symbol: str
    name: str
    market: str
    quantity: int
    avg_cost: float
    trade_date: str
    thesis_status: str | None = None       # linked thesis status, if any
    thesis_id: int | None = None


@dataclass(frozen=True, slots=True)
class PortfolioSummary:
    """Aggregated portfolio overview."""
    positions: list[PortfolioPosition] = field(default_factory=list)
    position_count: int = 0
    has_holdings: bool = False


class PortfolioAdapter:
    """Read-only adapter for V2 trades.db open positions.

    Does NOT create, update, or delete trade records.
    Only reads open positions and links them to Memory theses.
    """

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            db_dir = os.environ.get(
                "QUANT_DATA_DIR",
                os.environ.get("TRADING_DATA_DIR", r"D:\trading_data"),
            )
            db_path = os.path.join(db_dir, "trades.db")
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _table_exists(self) -> bool:
        """Check if the trades table exists."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name='trades'"
                ).fetchone()
                return row is not None
        except Exception:
            return False

    def get_open_positions(self) -> PortfolioSummary:
        """Get all open positions (unpaired buy records).

        Returns an empty PortfolioSummary if trades.db doesn't exist
        or has no open positions — never throws.
        """
        if not self._table_exists():
            return PortfolioSummary()

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM trades "
                "WHERE trade_type = '买入' AND paired_trade_id IS NULL "
                "ORDER BY trade_date DESC"
            ).fetchall()

        if not rows:
            return PortfolioSummary()

        positions = [
            PortfolioPosition(
                symbol=r["symbol"],
                name=r["name"],
                market=r["market"],
                quantity=r["quantity"],
                avg_cost=r["price"],
                trade_date=r["trade_date"],
            )
            for r in rows
        ]

        return PortfolioSummary(
            positions=positions,
            position_count=len(positions),
            has_holdings=True,
        )

    def enrich_with_thesis(
        self,
        summary: PortfolioSummary,
        memory_adapter: MemoryAdapter,
    ) -> PortfolioSummary:
        """Link each position to its active thesis in the Memory System.

        Modifies the PortfolioPosition.thesis_status and thesis_id fields
        by matching ticker symbols against pending theses.
        """
        active_theses = memory_adapter.get_active_theses()
        thesis_by_ticker: dict[str, ActiveThesis] = {}
        for t in active_theses:
            for ticker in t.ticker:
                thesis_by_ticker[ticker] = t

        enriched: list[PortfolioPosition] = []
        for pos in summary.positions:
            linked = thesis_by_ticker.get(pos.symbol)
            enriched.append(PortfolioPosition(
                symbol=pos.symbol,
                name=pos.name,
                market=pos.market,
                quantity=pos.quantity,
                avg_cost=pos.avg_cost,
                trade_date=pos.trade_date,
                thesis_status=linked.status if linked else None,
                thesis_id=linked.id if linked else None,
            ))

        return PortfolioSummary(
            positions=enriched,
            position_count=summary.position_count,
            has_holdings=summary.has_holdings,
        )


# ═══════════════════════════════════════════════════════════════
# Projection helpers — MemoryEntry → workspace dataclass
# ═══════════════════════════════════════════════════════════════

def _extract_priority(tags: list[str]) -> str:
    for tag in tags:
        if tag.startswith("priority:"):
            return tag.split(":", 1)[1]
    return "med"


def _to_watchlist(entry) -> WatchlistItem:
    return WatchlistItem(
        id=entry.id,
        ticker=entry.ticker,
        title=entry.title,
        content=entry.content,
        tags=entry.tags,
        priority=_extract_priority(entry.tags),
        created_at=entry.created_at,
    )


def _to_queue(entry) -> QueueItem:
    return QueueItem(
        id=entry.id,
        ticker=entry.ticker,
        title=entry.title,
        content=entry.content,
        tags=entry.tags,
        priority=_extract_priority(entry.tags),
        created_at=entry.created_at,
    )


def _to_active_thesis(entry) -> ActiveThesis:
    return ActiveThesis(
        id=entry.id,
        ticker=entry.ticker,
        title=entry.title,
        content=entry.content,
        thesis=entry.thesis,
        confidence=entry.confidence,
        tags=entry.tags,
        created_at=entry.created_at,
    )
