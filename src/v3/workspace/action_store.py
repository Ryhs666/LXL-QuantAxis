"""Action State Persistence — dedicated action_states table.

NOT stored in memory_entries. Action state is system runtime data,
not investment memory. Mixing them pollutes Journal, FTS5, and Analytics.

Schema is idempotent — safe to call initialize() repeatedly.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.v3.memory.config import MemoryConfig

# ═══════════════════════════════════════════════════════════════
# DDL
# ═══════════════════════════════════════════════════════════════

CREATE_ACTION_STATES = """
CREATE TABLE IF NOT EXISTS action_states (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    action_key          TEXT    NOT NULL UNIQUE,
    rule_code           TEXT    NOT NULL,
    object_type         TEXT    NOT NULL,
    object_id           TEXT    NOT NULL,
    ticker              TEXT    NOT NULL DEFAULT '',
    state               TEXT    NOT NULL DEFAULT 'active'
                        CHECK (state IN ('active', 'snoozed', 'dismissed', 'completed')),
    snoozed_until       TEXT,
    dismissed_until     TEXT,
    completed_at        TEXT,
    dismiss_reason      TEXT,
    condition_fingerprint TEXT,
    metadata_json       TEXT    NOT NULL DEFAULT '{}',
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

CREATE_INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_action_states_key ON action_states(action_key);",
    "CREATE INDEX IF NOT EXISTS idx_action_states_rule ON action_states(rule_code);",
    "CREATE INDEX IF NOT EXISTS idx_action_states_state ON action_states(state);",
    "CREATE INDEX IF NOT EXISTS idx_action_states_ticker ON action_states(ticker);",
    "CREATE INDEX IF NOT EXISTS idx_action_states_snoozed ON action_states(snoozed_until);",
    "CREATE INDEX IF NOT EXISTS idx_action_states_dismissed ON action_states(dismissed_until);",
]

MIGRATE_CLEANUP = """
DELETE FROM memory_entries WHERE tags LIKE '%action_state%';
"""


# ═══════════════════════════════════════════════════════════════
# Reactivation Policy (per-rule)
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class ReactivationPolicy:
    """Rule-specific policy for re-displaying completed actions."""

    rule_code: str
    recheck_days: int = 7          # days before re-evaluating condition
    recheck_description: str = ""

    def should_reactivate(self, completed_at: str, condition_still_exists: bool) -> bool:
        """Check if a completed action should re-activate."""
        if not condition_still_exists:
            return False
        if not completed_at:
            return True
        try:
            dt = datetime.fromisoformat(completed_at.replace(" ", "T")[:19])
            return (datetime.now() - dt).days >= self.recheck_days
        except (ValueError, TypeError):
            return True


REACTIVATION_POLICIES: dict[str, ReactivationPolicy] = {
    "R01_STALE_THESIS": ReactivationPolicy(
        "R01_STALE_THESIS", recheck_days=7,
        recheck_description="Thesis updated_at changed → resolved. Not updated → reactivate after 7d.",
    ),
    "R02_OVERDUE_REVIEW": ReactivationPolicy(
        "R02_OVERDUE_REVIEW", recheck_days=7,
        recheck_description="Last reviewed updated → resolved. Not reviewed → reactivate after 7d.",
    ),
    "R03_STALE_QUEUE": ReactivationPolicy(
        "R03_STALE_QUEUE", recheck_days=3,
        recheck_description="Queue item done or priority lowered → resolved. Still active → reactivate after 3d.",
    ),
    "R04_UNCOVERED_POSITION": ReactivationPolicy(
        "R04_UNCOVERED_POSITION", recheck_days=7,
        recheck_description="Valid thesis created → resolved. Still uncovered → reactivate after 7d.",
    ),
    "R05_CONCENTRATION_BREACH": ReactivationPolicy(
        "R05_CONCENTRATION_BREACH", recheck_days=3,
        recheck_description="Concentration below threshold → resolved. Still above → reactivate after 3d.",
    ),
    "R06_HIGH_CONVICTION_IDLE": ReactivationPolicy(
        "R06_HIGH_CONVICTION_IDLE", recheck_days=7,
        recheck_description="Decision recorded → resolved. No decision → reactivate after 7d.",
    ),
    "R07_DORMANT_WATCHLIST": ReactivationPolicy(
        "R07_DORMANT_WATCHLIST", recheck_days=7,
        recheck_description="Activity recorded → resolved. Still dormant → reactivate after 7d.",
    ),
    "R08_INVALIDATED_THESIS_STILL_HELD": ReactivationPolicy(
        "R08_INVALIDATED_THESIS_STILL_HELD", recheck_days=1,
        recheck_description="Position closed or new thesis → resolved. Still held → reactivate after 1d.",
    ),
    "R09_UNRESOLVED_COUNTER_EVIDENCE": ReactivationPolicy(
        "R09_UNRESOLVED_COUNTER_EVIDENCE", recheck_days=7,
        recheck_description="Evidence reviewed → resolved. Not reviewed → reactivate after 7d.",
    ),
    "R10_POSITION_CONVICTION_MISMATCH": ReactivationPolicy(
        "R10_POSITION_CONVICTION_MISMATCH", recheck_days=7,
        recheck_description="Position/conviction aligned → resolved. Still mismatched → reactivate after 7d.",
    ),
}


# ═══════════════════════════════════════════════════════════════
# Repository
# ═══════════════════════════════════════════════════════════════

class ActionStateRepository:
    """CRUD for the action_states table. Parameterized queries. Idempotent init."""

    def __init__(self, config: MemoryConfig | None = None) -> None:
        self._config = config or MemoryConfig.with_defaults()
        self._db_path = str(self._config.db_path)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
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

    def initialize(self) -> None:
        """Idempotent schema creation. Also cleans up any stale memory_entries pollution."""
        with self.connection() as conn:
            conn.executescript(CREATE_ACTION_STATES)
            for idx_sql in CREATE_INDEXES:
                conn.execute(idx_sql)
            # Clean up any action_state records previously stored in memory_entries
            with suppress(Exception):
                conn.execute(MIGRATE_CLEANUP)

    def is_initialized(self) -> bool:
        try:
            with self.connection() as conn:
                row = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='action_states'"
                ).fetchone()
                return row is not None
        except Exception:
            return False

    # ── CRUD ──────────────────────────────────────────────

    def get(self, action_key: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM action_states WHERE action_key = ?", (action_key,)
            ).fetchone()
        return dict(row) if row else None

    def upsert(self, action_key: str, **fields: Any) -> None:
        """Insert or update an action state row."""
        existing = self.get(action_key)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if existing:
            sets = []
            params: dict[str, Any] = {"key": action_key, "updated": now}
            for k, v in fields.items():
                if k in ("action_key", "id", "created_at"):
                    continue
                sets.append(f"{k} = :{k}")
                params[k] = v
            if not sets:
                return
            sets.append("updated_at = :updated")
            with self.connection() as conn:
                conn.execute(
                    f"UPDATE action_states SET {', '.join(sets)} WHERE action_key = :key",
                    params,
                )
        else:
            columns = ["action_key", "updated_at"]
            values = [":action_key", ":updated_at"]
            params = {"action_key": action_key, "updated_at": now}
            for k, v in fields.items():
                if k in ("id", "created_at"):
                    continue
                columns.append(k)
                values.append(f":{k}")
                params[k] = v
            if "rule_code" not in fields:
                columns.append("rule_code")
                values.append(":rule_code")
                params["rule_code"] = ""
            if "object_type" not in fields:
                columns.append("object_type")
                values.append(":object_type")
                params["object_type"] = ""
            if "object_id" not in fields:
                columns.append("object_id")
                values.append(":object_id")
                params["object_id"] = ""

            with self.connection() as conn:
                conn.execute(
                    f"INSERT INTO action_states ({', '.join(columns)}) "
                    f"VALUES ({', '.join(values)})",
                    params,
                )

    def list_by_state(self, state: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM action_states WHERE state = ?", (state,)
            ).fetchall()
        return [dict(r) for r in rows]

    def list_by_ticker(self, ticker: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM action_states WHERE ticker = ?", (ticker,)
            ).fetchall()
        return [dict(r) for r in rows]

    def delete(self, action_key: str) -> bool:
        with self.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM action_states WHERE action_key = ?", (action_key,)
            )
            return cursor.rowcount > 0


# ═══════════════════════════════════════════════════════════════
# State Manager (uses dedicated table)
# ═══════════════════════════════════════════════════════════════

class ActionStateManager:
    """Manages action lifecycle using the dedicated action_states table.

    State machine:
      active → snoozed (until snoozed_until) → active (after date)
      active → dismissed (cooldown_days) → active (after cooldown)
      active → completed → reactivation per ReactivationPolicy
    """

    def __init__(self, cooldown_days: int = 7) -> None:
        self._repo = ActionStateRepository()
        self._repo.initialize()
        self._cooldown_days = cooldown_days

    # ── Read ──────────────────────────────────────────────

    def get_state(self, action_key: str) -> dict[str, Any] | None:
        return self._repo.get(action_key)

    def is_suppressed(self, action_key: str) -> bool:
        """Check if an action should be hidden from display."""
        row = self._repo.get(action_key)
        if not row:
            return False

        state = row["state"]
        now = datetime.now()

        if state == "active":
            return False

        if state == "snoozed":
            until = row.get("snoozed_until")
            if until:
                try:
                    until_dt = datetime.fromisoformat(until.replace(" ", "T")[:19])
                    return now < until_dt
                except (ValueError, TypeError):
                    pass
            return False

        if state == "dismissed":
            # Cooldown: hide for cooldown_days
            dismissed_at = row.get("dismissed_until") or row.get("updated_at", "")
            if dismissed_at:
                try:
                    dt = datetime.fromisoformat(dismissed_at.replace(" ", "T")[:19])
                    return (now - dt).days < self._cooldown_days
                except (ValueError, TypeError):
                    pass
            return False

        # Completed actions are hidden from daily feed.
        # Reactivation is handled by should_reactivate().
        return state == "completed"

    def should_reactivate(self, action_key: str, rule_code: str, condition_exists: bool) -> bool:
        """Check if a completed action should reappear."""
        if not condition_exists:
            return False
        row = self._repo.get(action_key)
        if not row or row["state"] != "completed":
            return False

        policy = REACTIVATION_POLICIES.get(rule_code)
        if not policy:
            return False

        return policy.should_reactivate(row.get("completed_at", ""), condition_exists)

    # ── Write ─────────────────────────────────────────────

    def snooze(self, action_key: str, rule_code: str, object_type: str,
               object_id: str, ticker: str, until_date: str) -> None:
        self._repo.upsert(
            action_key,
            rule_code=rule_code, object_type=object_type, object_id=object_id,
            ticker=ticker, state="snoozed", snoozed_until=until_date,
        )

    def dismiss(self, action_key: str, rule_code: str, object_type: str,
                object_id: str, ticker: str, reason: str = "") -> None:
        cooldown_until = (datetime.now() + timedelta(days=self._cooldown_days)).strftime("%Y-%m-%d %H:%M:%S")
        self._repo.upsert(
            action_key,
            rule_code=rule_code, object_type=object_type, object_id=object_id,
            ticker=ticker, state="dismissed", dismissed_until=cooldown_until,
            dismiss_reason=reason,
        )

    def complete(self, action_key: str, rule_code: str, object_type: str,
                 object_id: str, ticker: str, fingerprint: str = "") -> None:
        self._repo.upsert(
            action_key,
            rule_code=rule_code, object_type=object_type, object_id=object_id,
            ticker=ticker, state="completed",
            completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            condition_fingerprint=fingerprint,
        )
