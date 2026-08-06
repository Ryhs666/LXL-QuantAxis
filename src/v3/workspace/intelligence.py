"""Workspace Intelligence — explainable Priority Action Engine.

Architecture: V3_INVESTMENT_DECISION_OS_ARCHITECTURE.md Section 11.

Pure computation + optional action_states persistence.
Zero new tables in Phase 2 MVP (action_states uses memory_entries).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.v3.workspace.repository import (
    ActiveThesis,
    MemoryAdapter,
    PortfolioAdapter,
    QueueItem,
    WatchlistItem,
)

# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class EngineConfig:
    """Centralized thresholds for the Priority Action Engine.

    All values can be overridden. No magic numbers in business logic.
    """

    # ── Time thresholds (days) ──
    stale_thesis_days: int = 45
    overdue_review_days: int = 30
    stale_queue_days: int = 5
    dormant_watchlist_days: int = 30
    conviction_idle_days: int = 14
    neglected_thesis_days: int = 60

    # ── Concentration thresholds ──
    single_position_warning_pct: float = 0.25
    single_position_critical_pct: float = 0.35
    sector_concentration_pct: float = 0.40
    theme_concentration_pct: float = 0.50

    # ── Conviction thresholds ──
    high_conviction_threshold: float = 0.70
    low_conviction_threshold: float = 0.50
    exposure_conviction_mismatch_ratio: float = 2.0

    # ── Display ──
    max_l1_actions: int = 5
    cooldown_days: int = 7


DEFAULT_CONFIG = EngineConfig()


# ═══════════════════════════════════════════════════════════════
# Action Candidate Model
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    """Explainable score components."""
    urgency: int = 0
    exposure: int = 0
    thesis_risk: int = 0
    overdue: int = 0
    evidence_conflict: int = 0


@dataclass(frozen=True, slots=True)
class ActionCandidate:
    """Unified action model — maps to architecture Section 11.2."""

    action_key: str                # stable: RULE_CODE:object_type:object_id
    rule_code: str                 # "R01_STALE_THESIS" etc.
    severity: str                  # "critical" | "warning" | "info"
    priority_score: int            # 0-100
    score_breakdown: ScoreBreakdown

    ticker: str                    # primary ticker
    title: str
    reason_text: str               # human-readable explanation
    reason_codes: list[str]        # machine-readable tags
    recommended_action: str        # suggested next step (never "buy now")

    linked_entry_ids: list[int]    # memory_entries.id(s)
    linked_thesis_id: int | None
    linked_position: str | None    # ticker of matched position

    due_date: str | None           # ISO date when action becomes overdue
    generated_at: str              # ISO datetime

    metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def make_key(rule_code: str, object_type: str, object_id: int) -> str:
        """Generate stable action_key. No date component — same problem = same key."""
        return f"{rule_code}:{object_type}:{object_id}"


# ═══════════════════════════════════════════════════════════════
# Thesis Health Model (upgraded)
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class ThesisHealth:
    """Multi-dimensional thesis health assessment."""

    thesis_id: int
    ticker: str

    freshness_status: str           # healthy | aging | stale | neglected
    freshness_days: int

    risk_flags: list[str]           # high_exposure, low_confidence, etc.
    health_reasons: list[str]       # human-readable explanations


# ═══════════════════════════════════════════════════════════════
# Priority Engine — 10 Rules, Unified Scoring
# ═══════════════════════════════════════════════════════════════

class PriorityEngine:
    """Generates prioritized, explainable action candidates.

    Uses unified component scoring:
      Priority Score = urgency + exposure + thesis_risk + overdue + evidence_conflict
      Normalized to 0-100.

    Severity mapping:
      CRITICAL: score >= 80
      WARNING:  score >= 50
      INFO:     score < 50

    Certain rules enforce severity floors regardless of computed score.
    """

    def __init__(
        self,
        memory: MemoryAdapter,
        portfolio: PortfolioAdapter,
        config: EngineConfig | None = None,
    ) -> None:
        self._memory = memory
        self._portfolio = portfolio
        self._config = config or DEFAULT_CONFIG

    # ── Public API ──────────────────────────────────────────

    def generate(self) -> list[ActionCandidate]:
        """Generate all action candidates sorted by priority_score DESC."""
        candidates: list[ActionCandidate] = []
        candidates.extend(self._r01_stale_thesis())
        candidates.extend(self._r02_overdue_review())
        candidates.extend(self._r03_stale_queue())
        candidates.extend(self._r04_uncovered_position())
        candidates.extend(self._r05_concentration_breach())
        candidates.extend(self._r06_high_conviction_idle())
        candidates.extend(self._r07_dormant_watchlist())
        candidates.extend(self._r08_invalidated_held())
        candidates.extend(self._r09_counter_evidence())
        candidates.extend(self._r10_conviction_mismatch())
        candidates.sort(key=lambda c: c.priority_score, reverse=True)
        return candidates

    def daily_focus(self, limit: int | None = None) -> list[ActionCandidate]:
        """Top-N actions for L1 display."""
        if limit is None:
            limit = self._config.max_l1_actions
        return self.generate()[:limit]

    # ═════════════════════════════════════════════════════════
    # R01: STALE_THESIS — >45 days without update
    # ═════════════════════════════════════════════════════════

    def _r01_stale_thesis(self) -> list[ActionCandidate]:
        candidates: list[ActionCandidate] = []
        for t in self._memory.get_active_theses():
            days = _days_since(t.created_at)
            if days <= self._config.stale_thesis_days:
                continue

            ticker_str = _ticker_str(t)
            urgency = min(35, 10 + (days - self._config.stale_thesis_days) // 3)
            overdue = min(35, (days - self._config.stale_thesis_days) // 2)
            thesis_risk = 20 if not _has_evidence(t) else 10

            score = min(100, urgency + overdue + thesis_risk)
            candidates.append(ActionCandidate(
                action_key=ActionCandidate.make_key("R01_STALE_THESIS", "thesis", t.id),
                rule_code="R01_STALE_THESIS",
                severity=_severity(score),
                priority_score=score,
                score_breakdown=ScoreBreakdown(urgency=urgency, overdue=overdue, thesis_risk=thesis_risk),
                ticker=ticker_str,
                title=f"{ticker_str}: thesis {days}d stale — needs update",
                reason_text=f"This thesis was created {days} days ago without update. Review catalysts, risks, and confidence.",
                reason_codes=["stale", f"days:{days}"],
                recommended_action="Review thesis: update catalysts, reassess risks, adjust confidence if needed. Consider marking outcome.",
                linked_entry_ids=[t.id],
                linked_thesis_id=t.id,
                linked_position=ticker_str if ticker_str else None,
                due_date=None,
                generated_at=_now(),
            ))
        return candidates

    # ═════════════════════════════════════════════════════════
    # R02: OVERDUE_REVIEW — >30 days without review
    # ═════════════════════════════════════════════════════════

    def _r02_overdue_review(self) -> list[ActionCandidate]:
        candidates: list[ActionCandidate] = []
        thresh = self._config.overdue_review_days
        for t in self._memory.get_active_theses():
            days = _days_since(t.created_at)
            if days <= thresh or days > self._config.stale_thesis_days:
                continue  # R01 covers >45d

            ticker_str = _ticker_str(t)
            urgency = min(25, 5 + (days - thresh))
            overdue = min(25, (days - thresh) * 2)
            thesis_risk = 15

            score = min(100, urgency + overdue + thesis_risk)
            candidates.append(ActionCandidate(
                action_key=ActionCandidate.make_key("R02_OVERDUE_REVIEW", "thesis", t.id),
                rule_code="R02_OVERDUE_REVIEW",
                severity=_severity(score),
                priority_score=score,
                score_breakdown=ScoreBreakdown(urgency=urgency, overdue=overdue, thesis_risk=thesis_risk),
                ticker=ticker_str,
                title=f"{ticker_str}: thesis {days}d old — schedule review",
                reason_text=f"This thesis is {days} days old. Schedule a review to assess catalyst progress and risk changes.",
                reason_codes=["overdue_review", f"days:{days}"],
                recommended_action="Schedule review: assess catalyst progress, risk changes, confidence adjustment.",
                linked_entry_ids=[t.id],
                linked_thesis_id=t.id,
                linked_position=ticker_str if ticker_str else None,
                due_date=None,
                generated_at=_now(),
            ))
        return candidates

    # ═════════════════════════════════════════════════════════
    # R03: STALE_HIGH_PRIORITY_QUEUE — >5 days
    # ═════════════════════════════════════════════════════════

    def _r03_stale_queue(self) -> list[ActionCandidate]:
        candidates: list[ActionCandidate] = []
        thresh = self._config.stale_queue_days
        for q in self._memory.get_queue():
            if q.priority != "high":
                continue
            days = _days_since(q.created_at)
            if days <= thresh:
                continue

            urgency = min(30, 10 + (days - thresh) * 3)
            overdue = min(20, (days - thresh) * 2)

            score = min(100, urgency + overdue)
            candidates.append(ActionCandidate(
                action_key=ActionCandidate.make_key("R03_STALE_QUEUE", "queue", q.id),
                rule_code="R03_STALE_QUEUE",
                severity=_severity(score),
                priority_score=score,
                score_breakdown=ScoreBreakdown(urgency=urgency, overdue=overdue),
                ticker=_ticker_str_q(q),
                title=f"High-priority task waiting {days}d: {q.title[:60]}",
                reason_text=f"Marked high-priority {days} days ago. Start researching or adjust priority.",
                reason_codes=["stale_queue", f"days:{days}", "priority:high"],
                recommended_action="Begin research today, or lower priority if no longer urgent.",
                linked_entry_ids=[q.id],
                linked_thesis_id=None,
                linked_position=None,
                due_date=None,
                generated_at=_now(),
            ))
        return candidates

    # ═════════════════════════════════════════════════════════
    # R04: UNCOVERED_POSITION — holding without thesis
    # ═════════════════════════════════════════════════════════

    def _r04_uncovered_position(self) -> list[ActionCandidate]:
        candidates: list[ActionCandidate] = []
        pf = self._portfolio.get_open_positions()
        thesis_tickers = {tk for t in self._memory.get_active_theses() for tk in t.ticker}

        for pos in pf.positions:
            if pos.symbol in thesis_tickers:
                continue

            exposure = 25  # baseline for uncovered
            overdue = 10
            score = min(100, exposure + overdue)
            # Severity floor: WARNING
            severity = "warning" if score < 50 else _severity(score)

            candidates.append(ActionCandidate(
                action_key=ActionCandidate.make_key("R04_UNCOVERED", "position", _pos_hash(pos.symbol)),
                rule_code="R04_UNCOVERED_POSITION",
                severity=severity,
                priority_score=score,
                score_breakdown=ScoreBreakdown(exposure=exposure, overdue=overdue),
                ticker=pos.symbol,
                title=f"{pos.symbol} ({pos.name}): holding without a thesis",
                reason_text=f"You hold {pos.quantity} shares of {pos.symbol} with no active investment thesis. Write one to clarify holding logic, target, and invalidation condition.",
                reason_codes=["uncovered_position", f"shares:{pos.quantity}"],
                recommended_action="Write an investment thesis for this holding. Define target, catalysts, risks, and invalidation condition.",
                linked_entry_ids=[],
                linked_thesis_id=None,
                linked_position=pos.symbol,
                due_date=None,
                generated_at=_now(),
            ))
        return candidates

    # ═════════════════════════════════════════════════════════
    # R05: CONCENTRATION_BREACH
    # ═════════════════════════════════════════════════════════

    def _r05_concentration_breach(self) -> list[ActionCandidate]:
        candidates: list[ActionCandidate] = []
        pf = self._portfolio.get_open_positions()
        if pf.position_count < 2:
            return candidates

        total_qty = sum(p.quantity for p in pf.positions)
        if total_qty == 0:
            return candidates

        critical_pct = self._config.single_position_critical_pct
        warning_pct = self._config.single_position_warning_pct

        for pos in pf.positions:
            ratio = pos.quantity / total_qty
            if ratio <= warning_pct:
                continue

            is_critical = ratio > critical_pct
            exposure = min(40, int(ratio * 80))
            thesis_risk = 10

            score = min(100, exposure + thesis_risk)
            severity = "critical" if is_critical else _severity(max(score, 50))

            candidates.append(ActionCandidate(
                action_key=ActionCandidate.make_key("R05_CONCENTRATION", "position", _pos_hash(pos.symbol)),
                rule_code="R05_CONCENTRATION_BREACH",
                severity=severity,
                priority_score=score,
                score_breakdown=ScoreBreakdown(exposure=exposure, thesis_risk=thesis_risk),
                ticker=pos.symbol,
                title=f"{pos.symbol}: {ratio:.0%} of portfolio — concentration {'critical' if is_critical else 'warning'}",
                reason_text=f"Position represents {ratio:.0%} of portfolio share count. {'Exceeds critical' if is_critical else 'Exceeds warning'} threshold of {critical_pct if is_critical else warning_pct:.0%}.",
                reason_codes=["concentration", f"ratio:{ratio:.0%}"],
                recommended_action="Review concentration risk. Consider diversification or stricter stop-loss.",
                linked_entry_ids=[],
                linked_thesis_id=None,
                linked_position=pos.symbol,
                due_date=None,
                generated_at=_now(),
            ))
        return candidates

    # ═════════════════════════════════════════════════════════
    # R06: HIGH_CONVICTION_IDLE — >14d no decision
    # ═════════════════════════════════════════════════════════

    def _r06_high_conviction_idle(self) -> list[ActionCandidate]:
        candidates: list[ActionCandidate] = []
        for t in self._memory.get_active_theses():
            if not t.confidence or t.confidence < self._config.high_conviction_threshold:
                continue
            days = _days_since(t.created_at)
            if days <= self._config.conviction_idle_days:
                continue

            ticker_str = _ticker_str(t)
            urgency = min(25, 5 + (days - self._config.conviction_idle_days))
            thesis_risk = int(t.confidence * 20)

            score = min(100, urgency + thesis_risk)
            candidates.append(ActionCandidate(
                action_key=ActionCandidate.make_key("R06_CONVICTION_IDLE", "thesis", t.id),
                rule_code="R06_HIGH_CONVICTION_IDLE",
                severity=_severity(score),
                priority_score=score,
                score_breakdown=ScoreBreakdown(urgency=urgency, thesis_risk=thesis_risk),
                ticker=ticker_str,
                title=f"{ticker_str}: high-conviction ({t.confidence:.0%}) thesis idle for {days}d",
                reason_text=f"Strong conviction but no recorded decision in {days} days. Review whether this thesis requires a recorded decision.",
                reason_codes=["conviction_idle", f"conviction:{t.confidence:.0%}", f"days:{days}"],
                recommended_action="Review whether this thesis requires a recorded decision.",
                linked_entry_ids=[t.id],
                linked_thesis_id=t.id,
                linked_position=ticker_str if ticker_str else None,
                due_date=None,
                generated_at=_now(),
            ))
        return candidates

    # ═════════════════════════════════════════════════════════
    # R07: DORMANT_WATCHLIST — >30d no activity
    # ═════════════════════════════════════════════════════════

    def _r07_dormant_watchlist(self) -> list[ActionCandidate]:
        candidates: list[ActionCandidate] = []
        for w in self._memory.get_watchlist():
            days = _days_since(w.created_at)
            if days <= self._config.dormant_watchlist_days:
                continue

            ticker_str = _ticker_str_w(w)
            urgency = min(20, 5 + (days - self._config.dormant_watchlist_days) // 5)
            overdue = min(15, (days - self._config.dormant_watchlist_days) // 3)

            score = min(100, urgency + overdue)
            candidates.append(ActionCandidate(
                action_key=ActionCandidate.make_key("R07_DORMANT_WATCHLIST", "watchlist", w.id),
                rule_code="R07_DORMANT_WATCHLIST",
                severity=_severity(score),
                priority_score=score,
                score_breakdown=ScoreBreakdown(urgency=urgency, overdue=overdue),
                ticker=ticker_str,
                title=f"{ticker_str}: watchlist {days}d with no activity",
                reason_text=f"On watchlist for {days} days without research activity. Begin research or remove from watchlist.",
                reason_codes=["dormant", f"days:{days}"],
                recommended_action="Begin preliminary research, or remove from watchlist if no longer relevant.",
                linked_entry_ids=[w.id],
                linked_thesis_id=None,
                linked_position=None,
                due_date=None,
                generated_at=_now(),
            ))
        return candidates

    # ═════════════════════════════════════════════════════════
    # R08: INVALIDATED_THESIS_STILL_HELD
    # ═════════════════════════════════════════════════════════

    def _r08_invalidated_held(self) -> list[ActionCandidate]:
        candidates: list[ActionCandidate] = []
        pf = self._portfolio.get_open_positions()
        position_tickers = {p.symbol for p in pf.positions}
        if not position_tickers:
            return candidates

        # Find all theses (not just active) with status='invalidated' or 'wrong'
        from src.v3.memory.search import MemorySearch, SearchFilters
        searcher = MemorySearch(self._memory._db)
        all_theses = searcher.query(SearchFilters(entry_type="thesis", limit=200))

        invalidated = [t for t in all_theses if hasattr(t, 'status') and t.status in ('invalidated', 'wrong')]

        for t in invalidated:
            for ticker in t.ticker:
                if ticker in position_tickers:
                    exposure = 35
                    thesis_risk = 30
                    score = min(100, exposure + thesis_risk)
                    # CRITICAL severity floor
                    severity = "critical"

                    candidates.append(ActionCandidate(
                        action_key=ActionCandidate.make_key("R08_INVALIDATED_HELD", "thesis", t.id),
                        rule_code="R08_INVALIDATED_THESIS_STILL_HELD",
                        severity=severity,
                        priority_score=score,
                        score_breakdown=ScoreBreakdown(exposure=exposure, thesis_risk=thesis_risk),
                        ticker=ticker,
                        title=f"{ticker}: thesis invalidated but position still held",
                        reason_text=f"The thesis for {ticker} was marked '{t.status}' but you still hold this position. Review urgently.",
                        reason_codes=["invalidated_held", f"thesis_status:{t.status}"],
                        recommended_action="Review this position immediately. Either write a new thesis or exit the position.",
                        linked_entry_ids=[t.id],
                        linked_thesis_id=t.id,
                        linked_position=ticker,
                        due_date=None,
                        generated_at=_now(),
                    ))
        return candidates

    # ═════════════════════════════════════════════════════════
    # R09: UNRESOLVED_COUNTER_EVIDENCE
    # ═════════════════════════════════════════════════════════

    def _r09_counter_evidence(self) -> list[ActionCandidate]:
        candidates: list[ActionCandidate] = []
        for t in self._memory.get_active_theses():
            evidence = (t.thesis or {}).get("evidence", {}) if t.thesis else {}
            counter = evidence.get("counter", [])
            if not counter:
                continue

            # Check if any counter evidence is newer than thesis last update
            # (Simplified: flag if counter evidence exists and thesis is >14d old)
            days = _days_since(t.created_at)
            if days < 14:
                continue

            ticker_str = _ticker_str(t)
            evidence_conflict = min(30, len(counter) * 10)
            thesis_risk = 20
            score = min(100, evidence_conflict + thesis_risk)
            # Severity floor: WARNING
            severity = "warning" if score < 50 else _severity(score)

            candidates.append(ActionCandidate(
                action_key=ActionCandidate.make_key("R09_COUNTER_EVIDENCE", "thesis", t.id),
                rule_code="R09_UNRESOLVED_COUNTER_EVIDENCE",
                severity=severity,
                priority_score=score,
                score_breakdown=ScoreBreakdown(evidence_conflict=evidence_conflict, thesis_risk=thesis_risk),
                ticker=ticker_str,
                title=f"{ticker_str}: {len(counter)} counter-evidence items not addressed",
                reason_text=f"Thesis has {len(counter)} pieces of counter-evidence that have not been reviewed in {days} days.",
                reason_codes=["counter_evidence", f"count:{len(counter)}", f"days:{days}"],
                recommended_action="Review counter-evidence. Decide: adjust thesis, add rebuttal evidence, or mark thesis invalidated.",
                linked_entry_ids=[t.id],
                linked_thesis_id=t.id,
                linked_position=ticker_str if ticker_str else None,
                due_date=None,
                generated_at=_now(),
            ))
        return candidates

    # ═════════════════════════════════════════════════════════
    # R10: POSITION_CONVICTION_MISMATCH
    # ═════════════════════════════════════════════════════════

    def _r10_conviction_mismatch(self) -> list[ActionCandidate]:
        candidates: list[ActionCandidate] = []
        pf = self._portfolio.get_open_positions()
        if pf.position_count == 0:
            return candidates

        total_qty = sum(p.quantity for p in pf.positions)
        if total_qty == 0:
            return candidates

        theses = self._memory.get_active_theses()
        thesis_map: dict[str, ActiveThesis] = {}
        for t in theses:
            for tk in t.ticker:
                thesis_map[tk] = t

        for pos in pf.positions:
            t = thesis_map.get(pos.symbol)
            if not t or not t.confidence:
                continue

            weight = pos.quantity / total_qty
            conf = t.confidence

            # Flag: weight > 15% AND confidence < 0.5
            if not (weight > 0.15 and conf < self._config.low_conviction_threshold):
                continue

            exposure = min(30, int(weight * 60))
            thesis_risk = int((1.0 - conf) * 25)
            score = min(100, exposure + thesis_risk)

            # Severity: severe mismatch (weight >25% or 3x conviction ratio) → CRITICAL
            is_severe = weight > 0.25 or (weight / max(conf, 0.01)) > 3.0
            severity = "critical" if is_severe else ("warning" if score < 50 else _severity(score))

            candidates.append(ActionCandidate(
                action_key=ActionCandidate.make_key("R10_CONVICTION_MISMATCH", "position", _pos_hash(pos.symbol)),
                rule_code="R10_POSITION_CONVICTION_MISMATCH",
                severity=severity,
                priority_score=score,
                score_breakdown=ScoreBreakdown(exposure=exposure, thesis_risk=thesis_risk),
                ticker=pos.symbol,
                title=f"{pos.symbol}: position ({weight:.0%}) exceeds thesis conviction ({conf:.0%})",
                reason_text=f"Your position weight ({weight:.0%}) is high relative to thesis confidence ({conf:.0%}). Consider reducing or strengthening evidence.",
                reason_codes=["conviction_mismatch", f"weight:{weight:.0%}", f"confidence:{conf:.0%}"],
                recommended_action="Consider reducing position size to match conviction level, or strengthen thesis with additional evidence.",
                linked_entry_ids=[t.id],
                linked_thesis_id=t.id,
                linked_position=pos.symbol,
                due_date=None,
                generated_at=_now(),
            ))
        return candidates


# ═══════════════════════════════════════════════════════════════
# Thesis Health Checker (upgraded)
# ═══════════════════════════════════════════════════════════════

class ThesisHealthChecker:
    """Multi-dimensional thesis health assessment.

    Returns freshness_status + risk_flags[] + health_reasons[].
    A single thesis can have multiple simultaneous risk flags.
    """

    def __init__(self, memory: MemoryAdapter, portfolio: PortfolioAdapter) -> None:
        self._memory = memory
        self._portfolio = portfolio
        self._config = DEFAULT_CONFIG

    def check_all(self) -> list[ThesisHealth]:
        return [self._check_one(t) for t in self._memory.get_active_theses()]

    def _check_one(self, t: ActiveThesis) -> ThesisHealth:
        days = _days_since(t.created_at)
        ticker_str = _ticker_str(t)
        flags: list[str] = []
        reasons: list[str] = []

        # Freshness
        if days > self._config.neglected_thesis_days:
            freshness = "neglected"
            reasons.append(f"No updates in {days} days.")
        elif days > self._config.stale_thesis_days:
            freshness = "stale"
            reasons.append(f"Thesis is {days} days old without update.")
        elif days > self._config.overdue_review_days:
            freshness = "aging"
            reasons.append(f"Thesis is {days} days old. Schedule review soon.")
        else:
            freshness = "healthy"

        # Risk flags
        conf = t.confidence or 0.5

        # Check portfolio exposure
        total_qty = sum(p.quantity for p in self._portfolio.get_open_positions().positions)
        for p in self._portfolio.get_open_positions().positions:
            if p.symbol in t.ticker and total_qty > 0:
                weight = p.quantity / total_qty
                if weight > self._config.single_position_warning_pct:
                    flags.append("high_exposure")
                    reasons.append(f"Position weight ({weight:.0%}) exceeds warning threshold.")

        if conf < self._config.low_conviction_threshold:
            flags.append("low_confidence")
            reasons.append(f"Low thesis confidence ({conf:.0%}).")

        evidence = (t.thesis or {}).get("evidence", {}) if t.thesis else {}
        if not evidence.get("supporting"):
            flags.append("no_supporting_evidence")
            reasons.append("No supporting evidence recorded.")
        if not evidence.get("counter"):
            flags.append("no_counter_evidence")
            reasons.append("No counter-evidence recorded — consider bear case.")
        if days > self._config.overdue_review_days:
            flags.append("overdue_review")
            reasons.append(f"Review overdue ({days} days since creation).")

        return ThesisHealth(
            thesis_id=t.id,
            ticker=ticker_str,
            freshness_status=freshness,
            freshness_days=days,
            risk_flags=flags,
            health_reasons=reasons,
        )


# ═══════════════════════════════════════════════════════════════
# Action State — re-exported from dedicated action_store module
# ═══════════════════════════════════════════════════════════════

from src.v3.workspace.action_store import (  # noqa: E402, F401
    ActionStateManager,
    ActionStateRepository,
    ReactivationPolicy,
)

# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _days_since(date_str: str) -> int:
    if not date_str:
        return 0
    try:
        dt = datetime.fromisoformat(date_str.replace(" ", "T")[:10])
        return (datetime.now() - dt).days
    except (ValueError, TypeError):
        return 0


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _severity(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 50:
        return "warning"
    return "info"


def _ticker_str(t: ActiveThesis) -> str:
    return ", ".join(t.ticker) if t.ticker else "?"


def _ticker_str_q(q: QueueItem) -> str:
    return ", ".join(q.ticker) if q.ticker else "—"


def _ticker_str_w(w: WatchlistItem) -> str:
    return ", ".join(w.ticker) if w.ticker else "—"


def _has_evidence(t: ActiveThesis) -> bool:
    if not t.thesis:
        return False
    evidence = t.thesis.get("evidence", {})
    return bool(evidence.get("supporting") or evidence.get("counter"))


def _pos_hash(symbol: str) -> int:
    """Deterministic hash for position-based action keys."""
    return abs(hash(symbol)) % (10**8)
