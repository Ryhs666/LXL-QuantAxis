"""SQLite repository for the expand-only Alpha Memory schema."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from src.lxl_quantaxis.memory.models import MemoryStrategy, ResearchNote, StrategyVersion
from src.lxl_quantaxis.memory.schema import downgrade, upgrade


class AlphaMemoryRepository:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def upgrade(self) -> None:
        with self.connection() as connection:
            upgrade(connection)

    def downgrade(self) -> None:
        with self.connection() as connection:
            downgrade(connection)

    def add_note(self, note: ResearchNote) -> None:
        _validate_identity(note.note_id, note.organization_id)
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO memory_notes VALUES (?, ?, ?, ?, ?)",
                (note.note_id, note.organization_id, note.body, note.source, note.created_at.isoformat()),
            )

    def get_note(self, *, organization_id: str, note_id: str) -> ResearchNote | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM memory_notes WHERE organization_id = ? AND note_id = ?",
                (organization_id, note_id),
            ).fetchone()
        if row is None:
            return None
        from datetime import datetime

        return ResearchNote(
            row["note_id"],
            row["organization_id"],
            row["body"],
            datetime.fromisoformat(row["created_at"]),
            row["source"],
        )

    def add_strategy(self, strategy: MemoryStrategy) -> bool:
        _validate_identity(strategy.strategy_id, strategy.organization_id)
        with self.connection() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO memory_strategies VALUES (?, ?, ?, ?, ?)",
                (
                    strategy.strategy_id,
                    strategy.organization_id,
                    strategy.name,
                    strategy.created_at.isoformat(),
                    strategy.legacy_key,
                ),
            )
            return cursor.rowcount == 1

    def add_version(self, version: StrategyVersion) -> None:
        if version.version <= 0:
            raise ValueError("strategy version must be positive")
        with self.connection() as connection:
            owner = connection.execute(
                "SELECT organization_id FROM memory_strategies WHERE strategy_id = ?",
                (version.strategy_id,),
            ).fetchone()
            if owner is None or owner["organization_id"] != version.organization_id:
                raise ValueError("strategy does not belong to organization")
            connection.execute(
                "INSERT INTO memory_strategy_versions VALUES (?, ?, ?, ?, ?, ?)",
                (
                    version.strategy_id,
                    version.organization_id,
                    version.version,
                    version.specification_json,
                    version.created_at.isoformat(),
                    version.status.value,
                ),
            )

    def list_versions(self, *, organization_id: str, strategy_id: str) -> tuple[StrategyVersion, ...]:
        from datetime import datetime

        from src.lxl_quantaxis.memory.models import ConfirmationStatus

        with self.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM memory_strategy_versions WHERE organization_id = ? AND strategy_id = ? ORDER BY version",
                (organization_id, strategy_id),
            ).fetchall()
        return tuple(
            StrategyVersion(
                row["strategy_id"],
                row["organization_id"],
                row["version"],
                row["specification_json"],
                datetime.fromisoformat(row["created_at"]),
                ConfirmationStatus(row["status"]),
            )
            for row in rows
        )

    def import_legacy_strategy(self, strategy: MemoryStrategy, version: StrategyVersion) -> bool:
        if strategy.legacy_key is None:
            raise ValueError("legacy import requires a legacy key")
        inserted = self.add_strategy(strategy)
        if inserted:
            self.add_version(version)
        return inserted


def _validate_identity(record_id: str, organization_id: str) -> None:
    if not record_id.strip() or not organization_id.strip():
        raise ValueError("record and organization ids cannot be empty")
