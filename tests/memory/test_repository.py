from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from src.lxl_quantaxis.memory import (
    AlphaMemoryRepository,
    MemoryStrategy,
    ResearchNote,
    StrategyVersion,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class AlphaMemoryRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary.name) / "memory.db"
        self.repository = AlphaMemoryRepository(self.database)
        self.repository.upgrade()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_migration_upgrades_and_rolls_back_only_memory_tables(self) -> None:
        self.repository.downgrade()
        with closing(sqlite3.connect(self.database)) as connection:
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'memory_%'"
            ).fetchall()
        self.assertEqual(tables, [])

    def test_notes_are_isolated_by_organization(self) -> None:
        self.repository.add_note(ResearchNote("n-1", "org-a", "AI demand", NOW))
        self.assertIsNotNone(self.repository.get_note(organization_id="org-a", note_id="n-1"))
        self.assertIsNone(self.repository.get_note(organization_id="org-b", note_id="n-1"))

    def test_strategy_versions_are_immutable(self) -> None:
        strategy = MemoryStrategy("s-1", "org-a", "Trend", NOW)
        version = StrategyVersion("s-1", "org-a", 1, '{"rule":"close > ma20"}', NOW)
        self.repository.add_strategy(strategy)
        self.repository.add_version(version)
        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.add_version(version)
        self.assertEqual(self.repository.list_versions(organization_id="org-a", strategy_id="s-1"), (version,))

    def test_legacy_import_is_idempotent(self) -> None:
        strategy = MemoryStrategy("s-legacy", "org-a", "Legacy", NOW, legacy_key="legacy:7")
        version = StrategyVersion("s-legacy", "org-a", 1, "{}", NOW)
        self.assertTrue(self.repository.import_legacy_strategy(strategy, version))
        self.assertFalse(self.repository.import_legacy_strategy(strategy, version))
        self.assertEqual(len(self.repository.list_versions(organization_id="org-a", strategy_id="s-legacy")), 1)


if __name__ == "__main__":
    unittest.main()
