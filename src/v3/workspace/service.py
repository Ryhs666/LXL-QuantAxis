"""Workspace Data Service — aggregates Memory + Portfolio into dashboard data.

Pure composition layer. No database writes. No new tables.
All data comes from MemoryAdapter and PortfolioAdapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.v3.memory.database import MemoryDatabase
from src.v3.workspace.repository import (
    ActiveThesis,
    MemoryAdapter,
    PortfolioAdapter,
    PortfolioSummary,
    QueueItem,
    WatchlistItem,
)


@dataclass(frozen=True, slots=True)
class WorkspaceDashboard:
    """Complete dashboard data for the /workspace page."""

    # Stat bar counts
    active_thesis_count: int = 0
    watchlist_count: int = 0
    queue_count: int = 0
    pending_review_count: int = 0

    # Data panels
    active_theses: list[dict[str, Any]] = field(default_factory=list)
    watchlist: list[dict[str, Any]] = field(default_factory=list)
    queue: list[dict[str, Any]] = field(default_factory=list)
    pending_reviews: list[dict[str, Any]] = field(default_factory=list)
    portfolio: dict[str, Any] = field(default_factory=dict)
    recent_reflections: list[dict[str, Any]] = field(default_factory=list)


class WorkspaceService:
    """Aggregate data from Memory + V2 trades into workspace views.

    Usage:
        svc = WorkspaceService()
        dashboard = svc.get_dashboard()
        # → WorkspaceDashboard with all panels populated
    """

    def __init__(self) -> None:
        self._db = MemoryDatabase()
        self._memory = MemoryAdapter(self._db)
        self._portfolio = PortfolioAdapter()

    # ── Public API ─────────────────────────────────────────

    def get_dashboard(self) -> WorkspaceDashboard:
        """Build the full workspace dashboard in one call."""
        watchlist = self._memory.get_watchlist()
        queue = self._memory.get_queue()
        theses = self._memory.get_active_theses()
        reviews = self._memory.get_pending_reviews(min_age_days=30)

        # Portfolio with thesis linkage
        raw_portfolio = self._portfolio.get_open_positions()
        enriched = self._portfolio.enrich_with_thesis(raw_portfolio, self._memory)

        reflections = self._memory.get_recent_reflections(limit=5)

        return WorkspaceDashboard(
            active_thesis_count=len(theses),
            watchlist_count=len(watchlist),
            queue_count=len(queue),
            pending_review_count=len(reviews),

            active_theses=[_thesis_to_dict(t) for t in theses],
            watchlist=[_watchlist_to_dict(w) for w in watchlist],
            queue=[_queue_to_dict(q) for q in queue],
            pending_reviews=reviews,
            portfolio=_portfolio_to_dict(enriched),
            recent_reflections=reflections,
        )

    # ── Individual panel queries ───────────────────────────

    def get_active_theses(self) -> list[dict[str, Any]]:
        return [_thesis_to_dict(t) for t in self._memory.get_active_theses()]

    def get_watchlist(self) -> list[dict[str, Any]]:
        return [_watchlist_to_dict(w) for w in self._memory.get_watchlist()]

    def get_queue(self) -> list[dict[str, Any]]:
        return [_queue_to_dict(q) for q in self._memory.get_queue()]

    def get_portfolio(self) -> dict[str, Any]:
        raw = self._portfolio.get_open_positions()
        enriched = self._portfolio.enrich_with_thesis(raw, self._memory)
        return _portfolio_to_dict(enriched)

    def get_pending_reviews(self) -> list[dict[str, Any]]:
        return self._memory.get_pending_reviews(min_age_days=30)

    def add_watchlist(
        self, ticker: list[str], title: str, content: str = "",
        tags: list[str] | None = None, priority: str = "med",
    ) -> int:
        return self._memory.add_to_watchlist(ticker, title, content, tags, priority)

    def remove_watchlist(self, entry_id: int) -> bool:
        return self._memory.remove_from_watchlist(entry_id)

    def add_queue(
        self, title: str, ticker: list[str] | None = None,
        content: str = "", tags: list[str] | None = None, priority: str = "med",
    ) -> int:
        return self._memory.add_to_queue(title, ticker, content, tags, priority)

    def mark_queue_done(self, entry_id: int) -> bool:
        return self._memory.mark_queue_done(entry_id)

    def mark_thesis_outcome(
        self, entry_id: int, status: str, detail: str,
        return_pct: float | None = None,
    ) -> bool:
        return self._memory.mark_thesis_outcome(entry_id, status, detail, return_pct)

    # ── Intelligence Methods ───────────────────────────────

    def daily_focus(self, limit: int | None = None) -> dict[str, Any]:
        """Get today's priority actions with suppression + reactivation applied."""
        from src.v3.workspace.intelligence import ActionStateManager, PriorityEngine

        engine = PriorityEngine(self._memory, self._portfolio)
        all_actions = engine.generate()
        states = ActionStateManager()

        visible: list[dict[str, Any]] = []
        suppressed_count = 0
        for a in all_actions:
            # Check suppression (snooze/dismiss cooldown)
            if states.is_suppressed(a.action_key):
                suppressed_count += 1
                continue

            # Check reactivation for completed actions
            if states.should_reactivate(a.action_key, a.rule_code, condition_exists=True):
                pass  # Let it through — re-activate

            visible.append(_action_to_dict(a))

        visible = visible[:(limit or 5)]

        sev = {"critical": 0, "warning": 0, "info": 0}
        for a in all_actions:
            sev[a.severity] = sev.get(a.severity, 0) + 1

        return {
            "generated_at": _now(),
            "total": len(all_actions),
            "visible_count": len(visible),
            "suppressed_count": suppressed_count,
            "severity_counts": sev,
            "actions": visible,
        }

    def snooze_action(self, action_key: str, rule_code: str = "",
                      object_type: str = "", object_id: str = "",
                      ticker: str = "", until_date: str = "") -> None:
        from src.v3.workspace.intelligence import ActionStateManager
        ActionStateManager().snooze(
            action_key, rule_code, object_type, object_id, ticker, until_date,
        )

    def dismiss_action(self, action_key: str, rule_code: str = "",
                       object_type: str = "", object_id: str = "",
                       ticker: str = "", reason: str = "") -> None:
        from src.v3.workspace.intelligence import ActionStateManager
        ActionStateManager().dismiss(
            action_key, rule_code, object_type, object_id, ticker, reason,
        )

    def complete_action(self, action_key: str, rule_code: str = "",
                        object_type: str = "", object_id: str = "",
                        ticker: str = "", fingerprint: str = "") -> None:
        from src.v3.workspace.intelligence import ActionStateManager
        ActionStateManager().complete(
            action_key, rule_code, object_type, object_id, ticker, fingerprint,
        )

    def thesis_health(self) -> list[dict[str, Any]]:
        """Get multi-dimensional health for all active theses."""
        from src.v3.workspace.intelligence import ThesisHealthChecker
        checker = ThesisHealthChecker(self._memory, self._portfolio)
        return [
            {
                "thesis_id": h.thesis_id,
                "ticker": h.ticker,
                "freshness_status": h.freshness_status,
                "freshness_days": h.freshness_days,
                "risk_flags": h.risk_flags,
                "health_reasons": h.health_reasons,
            }
            for h in checker.check_all()
        ]


# ═══════════════════════════════════════════════════════════════
# Serialization
# ═══════════════════════════════════════════════════════════════

def _now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _action_to_dict(a) -> dict[str, Any]:
    return {
        "action_key": a.action_key,
        "rule_code": a.rule_code,
        "severity": a.severity,
        "priority_score": a.priority_score,
        "score_breakdown": {
            "urgency": a.score_breakdown.urgency,
            "exposure": a.score_breakdown.exposure,
            "thesis_risk": a.score_breakdown.thesis_risk,
            "overdue": a.score_breakdown.overdue,
            "evidence_conflict": a.score_breakdown.evidence_conflict,
        },
        "ticker": a.ticker,
        "title": a.title,
        "reason_text": a.reason_text,
        "reason_codes": a.reason_codes,
        "recommended_action": a.recommended_action,
        "linked_entry_ids": a.linked_entry_ids,
        "linked_thesis_id": a.linked_thesis_id,
        "linked_position": a.linked_position,
        "generated_at": a.generated_at,
    }


# ═══════════════════════════════════════════════════════════════
# Serialization helpers
# ═══════════════════════════════════════════════════════════════

def _thesis_to_dict(t: ActiveThesis) -> dict[str, Any]:
    return {
        "id": t.id, "ticker": t.ticker, "title": t.title,
        "content": t.content, "thesis": t.thesis,
        "confidence": t.confidence, "tags": t.tags,
        "created_at": t.created_at,
    }


def _watchlist_to_dict(w: WatchlistItem) -> dict[str, Any]:
    return {
        "id": w.id, "ticker": w.ticker, "title": w.title,
        "content": w.content, "tags": w.tags,
        "priority": w.priority, "created_at": w.created_at,
    }


def _queue_to_dict(q: QueueItem) -> dict[str, Any]:
    return {
        "id": q.id, "ticker": q.ticker, "title": q.title,
        "content": q.content, "tags": q.tags,
        "priority": q.priority, "created_at": q.created_at,
    }


def _portfolio_to_dict(p: PortfolioSummary) -> dict[str, Any]:
    return {
        "positions": [
            {
                "symbol": pos.symbol,
                "name": pos.name,
                "market": pos.market,
                "quantity": pos.quantity,
                "avg_cost": pos.avg_cost,
                "trade_date": pos.trade_date,
                "thesis_status": pos.thesis_status,
                "thesis_id": pos.thesis_id,
            }
            for pos in p.positions
        ],
        "position_count": p.position_count,
        "has_holdings": p.has_holdings,
    }
