"""Memory Analytics — aggregate statistics and confidence calibration.

Provides overview stats (totals, distributions, rates) and deeper
analysis of the relationship between self-assessed confidence and
actual outcomes — the core learning loop of the Investment Memory System.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.v3.memory.database import MemoryDatabase
from src.v3.memory.models import ENTRY_TYPES
from src.v3.memory.repository import _from_json

# ── Output models ─────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class MemoryStats:
    """Aggregate statistics for the memory system."""

    total_entries: int = 0

    # Type breakdown
    notes: int = 0
    theses: int = 0
    decisions: int = 0
    reflections: int = 0

    # Thesis quality
    active_theses: int = 0           # status = 'pending'
    thesis_hit_rate: float = 0.0     # correct / (correct + wrong)
    thesis_correct: int = 0
    thesis_wrong: int = 0
    thesis_pending: int = 0

    # Decision quality
    decision_win_rate: float = 0.0   # good / (good + bad)
    decision_good: int = 0
    decision_bad: int = 0

    # Activity
    streak_days: int = 0             # consecutive days with entries
    avg_confidence: float = 0.0      # mean thesis confidence

    # Top tags
    top_tags: list[tuple[str, int]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class CalibrationBucket:
    """Confidence calibration for one confidence range."""

    label: str                       # "High (0.7-1.0)"
    min_conf: float
    max_conf: float
    total: int = 0
    correct: int = 0
    wrong: int = 0
    hit_rate: float = 0.0


@dataclass(frozen=True, slots=True)
class CalibrationReport:
    """Full confidence calibration analysis."""

    buckets: list[CalibrationBucket] = field(default_factory=list)
    overall_hit_rate: float = 0.0
    is_calibrated: bool = False      # True if high-conf bucket outperforms low-conf
    insight: str = ""                # Human-readable interpretation


@dataclass(frozen=True, slots=True)
class TagPerformance:
    """Hit rate broken down by tag."""

    tag: str = ""
    total: int = 0
    correct: int = 0
    hit_rate: float = 0.0


# ── Analytics engine ──────────────────────────────────────────

class MemoryAnalytics:
    """Compute aggregate statistics and calibration from memory_entries.

    All queries are read-only. No side effects. Instantiate with a
    MemoryDatabase and call methods to get structured reports.

    Usage:
        db = MemoryDatabase(config)
        analytics = MemoryAnalytics(db)
        stats = analytics.get_stats()
        cal = analytics.get_calibration()
    """

    def __init__(self, db: MemoryDatabase) -> None:
        self._db = db

    # ── Overview statistics ────────────────────────────────

    def get_stats(self) -> MemoryStats:
        """Compute full aggregate statistics.

        Returns a MemoryStats dataclass suitable for dashboard display.
        """
        with self._db.connection() as conn:
            # Total counts
            total = conn.execute(
                "SELECT COUNT(*) FROM memory_entries"
            ).fetchone()[0]

            type_counts = {}
            for etype in ENTRY_TYPES:
                row = conn.execute(
                    "SELECT COUNT(*) FROM memory_entries WHERE type = ?",
                    (etype,),
                ).fetchone()
                type_counts[etype] = row[0] if row else 0

            # Thesis outcomes
            thesis_correct = conn.execute(
                "SELECT COUNT(*) FROM memory_entries "
                "WHERE type = 'thesis' AND status = 'correct'"
            ).fetchone()[0]

            thesis_wrong = conn.execute(
                "SELECT COUNT(*) FROM memory_entries "
                "WHERE type = 'thesis' AND status = 'wrong'"
            ).fetchone()[0]

            thesis_pending = conn.execute(
                "SELECT COUNT(*) FROM memory_entries "
                "WHERE type = 'thesis' AND status = 'pending'"
            ).fetchone()[0]

            resolved = thesis_correct + thesis_wrong
            hit_rate = thesis_correct / resolved if resolved > 0 else 0.0

            # Decision outcomes
            decision_good = conn.execute(
                "SELECT COUNT(*) FROM memory_entries "
                "WHERE type = 'decision' AND status = 'good'"
            ).fetchone()[0]

            decision_bad = conn.execute(
                "SELECT COUNT(*) FROM memory_entries "
                "WHERE type = 'decision' AND status = 'bad'"
            ).fetchone()[0]

            resolved_dec = decision_good + decision_bad
            win_rate = decision_good / resolved_dec if resolved_dec > 0 else 0.0

            # Average confidence (thesis only)
            avg_row = conn.execute(
                "SELECT AVG(confidence) FROM memory_entries "
                "WHERE type = 'thesis' AND confidence IS NOT NULL"
            ).fetchone()
            avg_confidence = round(avg_row[0], 3) if avg_row and avg_row[0] else 0.0

            # Compute these inside the with block (need live connection)
            streak = self._compute_streak(conn)
            top = self._top_tags(conn)

        return MemoryStats(
            total_entries=total,
            notes=type_counts.get("note", 0),
            theses=type_counts.get("thesis", 0),
            decisions=type_counts.get("decision", 0),
            reflections=type_counts.get("reflection", 0),
            active_theses=thesis_pending,
            thesis_hit_rate=round(hit_rate, 3),
            thesis_correct=thesis_correct,
            thesis_wrong=thesis_wrong,
            thesis_pending=thesis_pending,
            decision_win_rate=round(win_rate, 3),
            decision_good=decision_good,
            decision_bad=decision_bad,
            streak_days=streak,
            avg_confidence=avg_confidence,
            top_tags=top,
        )

    # ── Confidence calibration ─────────────────────────────

    def get_calibration(self) -> CalibrationReport:
        """Analyze confidence vs outcome for thesis entries.

        Splits theses into confidence buckets and computes hit rate
        per bucket. A well-calibrated investor has higher hit rates
        in higher-confidence buckets.
        """
        buckets_def = [
            ("Low (< 0.5)",      0.0, 0.49),
            ("Medium (0.5-0.7)", 0.5, 0.7),
            ("High (> 0.7)",     0.71, 1.0),
        ]

        buckets: list[CalibrationBucket] = []
        total_correct = 0
        total_resolved = 0

        with self._db.connection() as conn:
            for label, lo, hi in buckets_def:
                row = conn.execute(
                    "SELECT "
                    "  COUNT(*) AS total, "
                    "  SUM(CASE WHEN status = 'correct' THEN 1 ELSE 0 END) AS correct, "
                    "  SUM(CASE WHEN status = 'wrong' THEN 1 ELSE 0 END) AS wrong "
                    "FROM memory_entries "
                    "WHERE type = 'thesis' "
                    "  AND confidence >= ? AND confidence <= ? "
                    "  AND status IN ('correct', 'wrong')",
                    (lo, hi),
                ).fetchone()

                total = row["total"]
                correct = row["correct"] or 0
                wrong = row["wrong"] or 0
                bucket_hit = correct / total if total > 0 else 0.0

                buckets.append(CalibrationBucket(
                    label=label,
                    min_conf=lo,
                    max_conf=hi,
                    total=total,
                    correct=correct,
                    wrong=wrong,
                    hit_rate=round(bucket_hit, 3),
                ))

                total_correct += correct
                total_resolved += total

        overall = total_correct / total_resolved if total_resolved > 0 else 0.0

        # Calibration check: high-confidence bucket should outperform low
        high_bucket = buckets[2] if len(buckets) > 2 else None
        low_bucket = buckets[0] if buckets else None
        is_calibrated = (
            high_bucket is not None
            and low_bucket is not None
            and high_bucket.total >= 2
            and high_bucket.hit_rate > low_bucket.hit_rate
        )

        # Generate insight
        insight = self._generate_calibration_insight(
            buckets, overall, is_calibrated
        )

        return CalibrationReport(
            buckets=buckets,
            overall_hit_rate=round(overall, 3),
            is_calibrated=is_calibrated,
            insight=insight,
        )

    # ── Tag performance ────────────────────────────────────

    def get_tag_performance(self) -> list[TagPerformance]:
        """Compute thesis hit rate per tag.

        Since tags are stored as JSON arrays, we extract them in Python
        rather than trying to parse JSON in SQLite.
        """
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT tags, status FROM memory_entries "
                "WHERE type = 'thesis' AND status IN ('correct', 'wrong')"
            ).fetchall()

        # Aggregate in Python
        tag_stats: dict[str, dict[str, int]] = {}
        for row in rows:
            tags = _from_json(row["tags"], [])
            status = row["status"]
            for tag in tags:
                if tag not in tag_stats:
                    tag_stats[tag] = {"total": 0, "correct": 0}
                tag_stats[tag]["total"] += 1
                if status == "correct":
                    tag_stats[tag]["correct"] += 1

        results = [
            TagPerformance(
                tag=tag,
                total=stats["total"],
                correct=stats["correct"],
                hit_rate=round(stats["correct"] / stats["total"], 3),
            )
            for tag, stats in tag_stats.items()
        ]
        results.sort(key=lambda x: x.hit_rate, reverse=True)
        return results

    # ── Time-based stats ───────────────────────────────────

    def get_activity_timeline(self, days: int = 30) -> list[dict[str, Any]]:
        """Get daily entry counts for the last N days.

        Returns a list of {date, total, notes, theses, decisions, reflections}
        suitable for rendering a sparkline or calendar heatmap.
        """
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT "
                "  date(created_at) AS day, "
                "  COUNT(*) AS total, "
                "  SUM(CASE WHEN type = 'note' THEN 1 ELSE 0 END) AS notes, "
                "  SUM(CASE WHEN type = 'thesis' THEN 1 ELSE 0 END) AS theses, "
                "  SUM(CASE WHEN type = 'decision' THEN 1 ELSE 0 END) AS decisions, "
                "  SUM(CASE WHEN type = 'reflection' THEN 1 ELSE 0 END) AS reflections "
                "FROM memory_entries "
                "WHERE created_at >= date('now', 'localtime', ?) "
                "GROUP BY day "
                "ORDER BY day ASC",
                (f"-{days} days",),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_pending_reviews(
        self, min_days_since_creation: int = 30
    ) -> list[dict[str, Any]]:
        """Find thesis entries awaiting review, sorted by age.

        Args:
            min_days_since_creation: Only return theses older than this.
        """
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT id, title, ticker, confidence, "
                "  created_at, "
                "  CAST(julianday('now', 'localtime') - "
                "       julianday(created_at) AS INTEGER) AS days_since "
                "FROM memory_entries "
                "WHERE type = 'thesis' AND status = 'pending' "
                "  AND julianday('now', 'localtime') - julianday(created_at) >= ? "
                "ORDER BY days_since DESC",
                (min_days_since_creation,),
            ).fetchall()

        return [
            {
                "id": r["id"],
                "title": r["title"],
                "ticker": _from_json(r["ticker"], []),
                "confidence": r["confidence"],
                "created_at": r["created_at"],
                "days_since": r["days_since"],
            }
            for r in rows
        ]

    # ── Internal helpers ───────────────────────────────────

    @staticmethod
    def _compute_streak(conn) -> int:
        """Count consecutive days (ending today) with at least one entry."""
        rows = conn.execute(
            "SELECT DISTINCT date(created_at) AS day "
            "FROM memory_entries "
            "ORDER BY day DESC "
            "LIMIT 365"
        ).fetchall()

        if not rows:
            return 0

        from datetime import date, timedelta
        today = date.today()
        streak = 0
        for row in rows:
            entry_date = date.fromisoformat(row["day"])
            expected = today - timedelta(days=streak)
            if entry_date == expected:
                streak += 1
            elif entry_date < expected:
                break
        return streak

    @staticmethod
    def _top_tags(conn, limit: int = 10) -> list[tuple[str, int]]:
        """Extract most-used tags across all entries."""
        rows = conn.execute(
            "SELECT tags FROM memory_entries"
        ).fetchall()

        counter: dict[str, int] = {}
        for row in rows:
            tags = _from_json(row["tags"], [])
            for tag in tags:
                counter[tag] = counter.get(tag, 0) + 1

        sorted_tags = sorted(counter.items(), key=lambda x: x[1], reverse=True)
        return sorted_tags[:limit]

    @staticmethod
    def _generate_calibration_insight(
        buckets: list[CalibrationBucket],
        overall: float,
        is_calibrated: bool,
    ) -> str:
        """Generate a human-readable insight from calibration data."""
        if not buckets or all(b.total == 0 for b in buckets):
            return "Not enough data yet. Create and review at least 3 theses to see calibration."

        high = buckets[-1] if buckets else None
        low = buckets[0] if buckets else None

        if is_calibrated and high and low:
            return (
                f"Good calibration: your high-confidence theses ({high.label}) "
                f"hit at {high.hit_rate:.0%}, vs {low.hit_rate:.0%} for low-confidence. "
                f"You know when you know."
            )
        elif high and low and high.total >= 2 and high.hit_rate <= low.hit_rate:
            return (
                f"Needs attention: your high-confidence theses ({high.label}) "
                f"underperform low-confidence ones ({low.hit_rate:.0%} vs {high.hit_rate:.0%}). "
                f"Re-examine what gives you conviction."
            )
        elif overall >= 0.6:
            return f"Overall thesis hit rate is {overall:.0%}. Keep tracking to build statistical confidence."
        else:
            return (
                f"Overall hit rate is {overall:.0%}. Focus on reviewing pending theses "
                f"and logging lessons to identify your edge."
            )
