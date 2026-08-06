"""Workspace Intelligence — Priority Engine, Attention Scoring, Thesis Health.

Pure computation layer. No database writes. No new tables.
All analysis derived from existing MemoryAdapter + PortfolioAdapter data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.v3.workspace.repository import (
    ActiveThesis,
    MemoryAdapter,
    PortfolioAdapter,
    QueueItem,
    WatchlistItem,
)

# ═══════════════════════════════════════════════════════════════
# Output Models
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class PriorityAction:
    """A single action item for the investor's attention."""

    action_id: str               # "review-thesis-42"
    level: str                   # "critical" | "warning" | "info"
    category: str                # "review" | "research" | "decide" | "risk"
    title: str
    description: str
    source_type: str             # "thesis" | "queue" | "position" | "watchlist"
    source_id: int               # entry_id
    priority_score: int          # 0-100 (higher = more urgent)
    days_stale: int = 0


@dataclass(frozen=True, slots=True)
class AttentionScore:
    """Scored attention level for a workspace item."""

    item_id: int
    item_type: str               # "watchlist" | "queue" | "thesis"
    score: int                   # 0-100
    factors: dict[str, int] = field(default_factory=dict)
    # factors breakdown: urgency, importance, relevance, staleness


@dataclass(frozen=True, slots=True)
class ThesisHealth:
    """Health assessment for a single thesis."""

    thesis_id: int
    status: str                  # "healthy" | "aging" | "stale" | "at_risk" | "neglected"
    days_since_created: int
    days_since_updated: int
    has_evidence: bool
    has_review: bool
    recommendation: str


# ═══════════════════════════════════════════════════════════════
# Priority Engine
# ═══════════════════════════════════════════════════════════════

class PriorityEngine:
    """Scans all workspace data and generates prioritized action items.

    Uses a multi-factor scoring formula:
      Priority Score = Urgency x Importance x Relevance x Overdue Weight

    The engine does NOT write to the database. It is a pure read-and-compute
    layer. Actions are generated fresh on every call — no caching, no state.
    """

    def __init__(
        self,
        memory: MemoryAdapter,
        portfolio: PortfolioAdapter,
    ) -> None:
        self._memory = memory
        self._portfolio = portfolio

    def generate_actions(self) -> list[PriorityAction]:
        """Generate all priority actions, sorted by score descending."""
        actions: list[PriorityAction] = []

        actions.extend(self._scan_stale_theses())
        actions.extend(self._scan_overdue_reviews())
        actions.extend(self._scan_stale_queue())
        actions.extend(self._scan_uncovered_positions())
        actions.extend(self._scan_concentration_risk())
        actions.extend(self._scan_high_conviction_idle())
        actions.extend(self._scan_dormant_watchlist())

        actions.sort(key=lambda a: a.priority_score, reverse=True)
        return actions

    def daily_focus(self, limit: int = 5) -> list[PriorityAction]:
        """Get today's top priority actions (limited)."""
        all_actions = self.generate_actions()
        return all_actions[:limit]

    # ── Rule Scanners ──────────────────────────────────────

    def _scan_stale_theses(self) -> list[PriorityAction]:
        """Rule 1: Thesis > 45 days without update → CRITICAL."""
        actions: list[PriorityAction] = []
        for t in self._memory.get_active_theses():
            days = self._days_since(t.created_at)
            if days > 45:
                tickers = ", ".join(t.ticker) if t.ticker else "?"
                score = min(100, 60 + (days - 45))
                actions.append(PriorityAction(
                    action_id=f"review-thesis-{t.id}",
                    level="critical",
                    category="review",
                    title=f"{tickers} thesis {days}d stale — needs update",
                    description=(
                        f"This thesis was created {days} days ago without an update. "
                        f"Review: have catalysts triggered? Have risks changed? "
                        f"Should confidence be adjusted?"
                    ),
                    source_type="thesis",
                    source_id=t.id,
                    priority_score=score,
                    days_stale=days,
                ))
        return actions

    def _scan_overdue_reviews(self) -> list[PriorityAction]:
        """Rule 2: Thesis > 30 days without review → WARNING."""
        actions: list[PriorityAction] = []
        for t in self._memory.get_active_theses():
            days = self._days_since(t.created_at)
            if 30 < days <= 45:
                tickers = ", ".join(t.ticker) if t.ticker else "?"
                score = min(80, 40 + (days - 30))
                actions.append(PriorityAction(
                    action_id=f"review-thesis-{t.id}",
                    level="warning",
                    category="review",
                    title=f"{tickers} thesis {days}d old — schedule review",
                    description=(
                        f"This thesis is {days} days old. Schedule a review to assess "
                        f"catalyst progress, risk changes, and confidence adjustment."
                    ),
                    source_type="thesis",
                    source_id=t.id,
                    priority_score=score,
                    days_stale=days,
                ))
        return actions

    def _scan_stale_queue(self) -> list[PriorityAction]:
        """Rule 3: High-priority queue item > 5 days → WARNING."""
        actions: list[PriorityAction] = []
        for q in self._memory.get_queue():
            if q.priority != "high":
                continue
            days = self._days_since(q.created_at)
            if days > 5:
                score = min(70, 35 + (days - 5) * 3)
                actions.append(PriorityAction(
                    action_id=f"research-queue-{q.id}",
                    level="warning",
                    category="research",
                    title=f"High-priority task waiting {days}d: {q.title[:60]}",
                    description=(
                        f"This research task was marked high-priority {days} days ago. "
                        f"Start researching today, or adjust priority if it's no longer urgent."
                    ),
                    source_type="queue",
                    source_id=q.id,
                    priority_score=score,
                    days_stale=days,
                ))
        return actions

    def _scan_uncovered_positions(self) -> list[PriorityAction]:
        """Rule 4: Position without active thesis → WARNING."""
        actions: list[PriorityAction] = []
        pf = self._portfolio.get_open_positions()
        theses = self._memory.get_active_theses()
        thesis_tickers = {tk for t in theses for tk in t.ticker}

        for pos in pf.positions:
            if pos.symbol not in thesis_tickers:
                actions.append(PriorityAction(
                    action_id=f"uncovered-{pos.symbol}",
                    level="warning",
                    category="decide",
                    title=f"{pos.symbol} ({pos.name}): holding without a thesis",
                    description=(
                        f"You hold {pos.quantity} shares of {pos.symbol} but have no "
                        f"active investment thesis. Write one to clarify your holding "
                        f"logic, target, and invalidation condition."
                    ),
                    source_type="position",
                    source_id=0,
                    priority_score=55,
                ))
        return actions

    def _scan_concentration_risk(self) -> list[PriorityAction]:
        """Rule 5: Single position > 25% portfolio → WARNING."""
        actions: list[PriorityAction] = []
        pf = self._portfolio.get_open_positions()

        # Estimate weight by share count (price not available from trades.db alone)
        # Simple heuristic: count positions and flag if any dominates by quantity
        if pf.position_count >= 2:
            max_pos = max(pf.positions, key=lambda p: p.quantity, default=None)
            total_qty = sum(p.quantity for p in pf.positions)
            if max_pos and total_qty > 0:
                ratio = max_pos.quantity / total_qty
                if ratio > 0.35:
                    actions.append(PriorityAction(
                        action_id=f"concentration-{max_pos.symbol}",
                        level="warning",
                        category="risk",
                        title=f"{max_pos.symbol} dominates portfolio ({ratio:.0%} of shares)",
                        description=(
                            f"Your position in {max_pos.symbol} represents {ratio:.0%} of "
                            f"total share count. Review concentration risk and consider "
                            f"diversification or stricter stop-loss."
                        ),
                        source_type="position",
                        source_id=0,
                        priority_score=50,
                    ))
        return actions

    def _scan_high_conviction_idle(self) -> list[PriorityAction]:
        """Rule 6: High-confidence thesis > 14d with no decision → INFO."""
        actions: list[PriorityAction] = []
        for t in self._memory.get_active_theses():
            if not t.confidence or t.confidence < 0.7:
                continue
            days = self._days_since(t.created_at)
            if days > 14:
                tickers = ", ".join(t.ticker) if t.ticker else "?"
                score = int(15 + t.confidence * 15)
                actions.append(PriorityAction(
                    action_id=f"idle-thesis-{t.id}",
                    level="info",
                    category="decide",
                    title=f"High-conviction thesis ({t.confidence:.0%}) idle for {days}d",
                    description=(
                        f"You have high conviction in {tickers} but haven't acted in "
                        f"{days} days. Is there a barrier? Is the entry point not right? "
                        f"Or does conviction need re-evaluation?"
                    ),
                    source_type="thesis",
                    source_id=t.id,
                    priority_score=score,
                    days_stale=days,
                ))
        return actions

    def _scan_dormant_watchlist(self) -> list[PriorityAction]:
        """Rule 7: Watchlist item > 30d with no activity → INFO."""
        actions: list[PriorityAction] = []
        for w in self._memory.get_watchlist():
            days = self._days_since(w.created_at)
            if days > 30:
                tickers = ", ".join(w.ticker) if w.ticker else "?"
                score = min(30, 5 + (days - 30))
                actions.append(PriorityAction(
                    action_id=f"dormant-watchlist-{w.id}",
                    level="info",
                    category="research",
                    title=f"{tickers} on watchlist {days}d with no activity",
                    description=(
                        f"This stock has been on your watchlist for {days} days "
                        f"without research activity. Start digging in, or remove "
                        f"from watchlist if no longer relevant."
                    ),
                    source_type="watchlist",
                    source_id=w.id,
                    priority_score=score,
                    days_stale=days,
                ))
        return actions

    @staticmethod
    def _days_since(date_str: str) -> int:
        """Calculate days between date_str and today."""
        if not date_str:
            return 0
        try:
            dt = datetime.fromisoformat(date_str.replace(" ", "T")[:10])
            return (datetime.now() - dt).days
        except (ValueError, TypeError):
            return 0


# ═══════════════════════════════════════════════════════════════
# Attention Scorer
# ═══════════════════════════════════════════════════════════════

class AttentionScorer:
    """Compute 0-100 attention scores for workspace items.

    Factors:
      urgency:    How time-sensitive is this? (0-40)
      importance: How financially significant? (0-30)
      relevance:  How relevant to current portfolio? (0-20)
      staleness:  How long since last activity? (0-10)
    """

    def __init__(self, memory: MemoryAdapter, portfolio: PortfolioAdapter) -> None:
        self._memory = memory
        self._portfolio = portfolio
        self._position_tickers: set[str] = set()
        self._load_portfolio_context()

    def _load_portfolio_context(self) -> None:
        """Load portfolio tickers for relevance scoring."""
        pf = self._portfolio.get_open_positions()
        self._position_tickers = {p.symbol for p in pf.positions}

    def score_watchlist(self, item: WatchlistItem) -> AttentionScore:
        """Score a watchlist item."""
        days = PriorityEngine._days_since(item.created_at)

        urgency = 5 if days < 7 else 15 if days < 30 else 25
        importance = 15 if item.priority == "high" else 10 if item.priority == "med" else 5
        relevance = 20 if any(t in self._position_tickers for t in item.ticker) else 5
        staleness = min(10, days // 10)

        total = urgency + importance + relevance + staleness
        return AttentionScore(
            item_id=item.id, item_type="watchlist", score=min(100, total),
            factors={"urgency": urgency, "importance": importance,
                     "relevance": relevance, "staleness": staleness},
        )

    def score_queue(self, item: QueueItem) -> AttentionScore:
        """Score a research queue item."""
        days = PriorityEngine._days_since(item.created_at)

        urgency = 5 if days < 3 else 20 if days < 7 else 35
        importance = 20 if item.priority == "high" else 12 if item.priority == "med" else 5
        relevance = 15 if any(t in self._position_tickers for t in item.ticker) else 5
        staleness = min(10, days // 7)

        total = urgency + importance + relevance + staleness
        return AttentionScore(
            item_id=item.id, item_type="queue", score=min(100, total),
            factors={"urgency": urgency, "importance": importance,
                     "relevance": relevance, "staleness": staleness},
        )

    def score_thesis(self, thesis: ActiveThesis) -> AttentionScore:
        """Score an active thesis."""
        days = PriorityEngine._days_since(thesis.created_at)

        urgency = 5 if days < 14 else 15 if days < 30 else 25 if days < 45 else 35
        importance = int((thesis.confidence or 0.5) * 25)
        relevance = 20 if any(t in self._position_tickers for t in thesis.ticker) else 5
        staleness = min(10, days // 15)

        total = urgency + importance + relevance + staleness
        return AttentionScore(
            item_id=thesis.id, item_type="thesis", score=min(100, total),
            factors={"urgency": urgency, "importance": importance,
                     "relevance": relevance, "staleness": staleness},
        )

    def attention_items(self) -> list[AttentionScore]:
        """Get all items ranked by attention score."""
        scores: list[AttentionScore] = []
        for w in self._memory.get_watchlist():
            scores.append(self.score_watchlist(w))
        for q in self._memory.get_queue():
            scores.append(self.score_queue(q))
        for t in self._memory.get_active_theses():
            scores.append(self.score_thesis(t))
        scores.sort(key=lambda s: s.score, reverse=True)
        return scores


# ═══════════════════════════════════════════════════════════════
# Thesis Health Checker
# ═══════════════════════════════════════════════════════════════

class ThesisHealthChecker:
    """Evaluate health status for each active thesis.

    Statuses:
      healthy   — Recently created/updated, actively maintained
      aging     — 30-45 days old, no review yet
      stale     — >45 days old, needs attention
      at_risk   — High portfolio exposure + low confidence
      neglected — >60 days without any update
    """

    def __init__(self, memory: MemoryAdapter, portfolio: PortfolioAdapter) -> None:
        self._memory = memory
        self._portfolio = portfolio
        self._position_tickers: dict[str, float] = {}
        self._load_portfolio()

    def _load_portfolio(self) -> None:
        """Map ticker → estimated weight for risk assessment."""
        pf = self._portfolio.get_open_positions()
        total_qty = sum(p.quantity for p in pf.positions)
        if total_qty > 0:
            self._position_tickers = {
                p.symbol: p.quantity / total_qty for p in pf.positions
            }

    def check_all(self) -> list[ThesisHealth]:
        """Evaluate health for all active theses."""
        return [self.check_one(t) for t in self._memory.get_active_theses()]

    def check_one(self, thesis: ActiveThesis) -> ThesisHealth:
        """Evaluate health for a single thesis."""
        days_created = PriorityEngine._days_since(thesis.created_at)
        days_updated = days_created  # Fallback: no separate updated tracking yet

        has_evidence = bool(thesis.thesis and thesis.thesis.get("evidence"))
        has_review = bool(thesis.thesis and thesis.thesis.get("outcome"))

        # Determine status
        confidence = thesis.confidence or 0.5
        exposure = 0.0
        for ticker in thesis.ticker:
            exposure = max(exposure, self._position_tickers.get(ticker, 0.0))

        if exposure > 0.15 and confidence < 0.5:
            status = "at_risk"
            recommendation = (
                f"High exposure ({exposure:.0%}) with low confidence ({confidence:.0%}). "
                f"Consider reducing position or strengthening thesis evidence."
            )
        elif days_created > 60:
            status = "neglected"
            recommendation = (
                f"No updates in {days_created} days. This thesis needs immediate "
                f"review or closure."
            )
        elif days_created > 45:
            status = "stale"
            recommendation = (
                f"Thesis is {days_created} days old. Review catalysts, risks, "
                f"and confidence. Consider marking outcome if catalysts played out."
            )
        elif days_created > 30:
            status = "aging"
            recommendation = (
                f"Thesis is aging ({days_created} days). Schedule a review "
                f"to ensure the investment logic still holds."
            )
        else:
            status = "healthy"
            recommendation = "Thesis is current and actively maintained."

        return ThesisHealth(
            thesis_id=thesis.id,
            status=status,
            days_since_created=days_created,
            days_since_updated=days_updated,
            has_evidence=has_evidence,
            has_review=has_review,
            recommendation=recommendation,
        )
