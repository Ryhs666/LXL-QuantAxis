from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from src.lxl_quantaxis.core.observability import InMemoryTelemetry, correlation_scope, reset_correlation, run_observed
from src.lxl_quantaxis.execution.orders import Order, OrderSide, OrderStatus
from src.lxl_quantaxis.execution.paper_trading import PaperBroker
from src.lxl_quantaxis.ops import OperationalKillSwitch, create_backup, evaluate_release, restore_backup


class FailingTelemetry:
    def emit(self, event: object) -> None:
        del event
        raise RuntimeError("collector unavailable")


class OperabilityTests(unittest.TestCase):
    def test_telemetry_failure_does_not_change_domain_result(self) -> None:
        self.assertEqual(run_observed("research", lambda: 42, sink=FailingTelemetry()), 42)

    def test_trace_correlation_is_propagated(self) -> None:
        sink = InMemoryTelemetry()
        token = correlation_scope("trace-1")
        try:
            run_observed("daily", lambda: "ok", sink=sink, attributes={"organization": "org-a"})
        finally:
            reset_correlation(token)
        self.assertEqual(sink.events[0].correlation_id, "trace-1")

    def test_backup_restore_drill_verifies_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup, restored = root / "source.db", root / "backup.db", root / "restored.db"
            with closing(sqlite3.connect(source)) as connection:
                connection.execute("CREATE TABLE facts(value TEXT)")
                connection.execute("INSERT INTO facts VALUES ('verified')")
                connection.commit()
            artifact = create_backup(source, backup)
            restore_backup(artifact, restored)
            with closing(sqlite3.connect(restored)) as connection:
                value = connection.execute("SELECT value FROM facts").fetchone()[0]
            self.assertEqual(value, "verified")

    def test_kill_switch_rejects_new_paper_orders_and_is_audited(self) -> None:
        switch = OperationalKillSwitch()
        switch.set(active=True, actor="risk-officer", reason="drill", occurred_at=datetime.now(UTC))
        broker = PaperBroker(initial_cash=Decimal("10000"), kill_switch=switch)
        order = Order("o-1", "600000", OrderSide.BUY, 100, datetime.now(UTC))
        self.assertIs(broker.submit(order).status, OrderStatus.REJECTED)
        self.assertEqual(switch.events[0].reason, "drill")

    def test_release_gate_fails_closed(self) -> None:
        results = dict.fromkeys(("tests", "types", "lint", "security", "build"), True)
        decision = evaluate_release(results)
        self.assertFalse(decision.approved)
        self.assertEqual(decision.failed_gates, ("backup_restore",))


if __name__ == "__main__":
    unittest.main()
