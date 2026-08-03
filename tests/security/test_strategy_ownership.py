"""Ownership isolation tests for the legacy strategy-bank adapter."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.data.strategy_store import StrategyBank


class StrategyOwnershipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "strategy-bank.db"
        self.bank = StrategyBank(str(database_path))

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_users_only_list_and_read_their_own_strategies(self) -> None:
        first_id = self.bank.save_strategy("first", [], owner_id=1)
        self.bank.save_strategy("second", [], owner_id=2)

        first_user_rows = self.bank.list_strategies(owner_id=1)

        self.assertEqual([row["id"] for row in first_user_rows], [first_id])
        self.assertIsNone(self.bank.get_strategy(first_id, owner_id=2))
        self.assertEqual(self.bank.get_strategy(first_id, owner_id=1)["name"], "first")

    def test_user_cannot_delete_another_users_strategy(self) -> None:
        strategy_id = self.bank.save_strategy("private", [], owner_id=1)

        self.assertFalse(self.bank.delete_strategy(strategy_id, owner_id=2))
        self.assertIsNotNone(self.bank.get_strategy(strategy_id, owner_id=1))
        self.assertTrue(self.bank.delete_strategy(strategy_id, owner_id=1))

    def test_only_admin_compatibility_path_can_access_legacy_unowned_rows(self) -> None:
        legacy_id = self.bank.save_strategy("legacy", [])

        self.assertIsNone(self.bank.get_strategy(legacy_id, owner_id=2))
        self.assertIsNotNone(
            self.bank.get_strategy(
                legacy_id,
                owner_id=1,
                include_unowned=True,
            )
        )

    def test_update_rejects_unknown_columns(self) -> None:
        strategy_id = self.bank.save_strategy("safe", [], owner_id=1)

        with self.assertRaisesRegex(ValueError, "不允许更新字段"):
            self.bank.update_strategy(
                strategy_id,
                owner_id=1,
                **{"name=?, owner_id": "unsafe"},
            )


if __name__ == "__main__":
    unittest.main()
