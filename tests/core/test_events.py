"""Behavior tests for immutable serializable domain events."""

import unittest

from src.lxl_quantaxis.core.contracts import Instant
from src.lxl_quantaxis.core.events import DomainEvent
from src.lxl_quantaxis.core.ids import CorrelationId, EventId, ResearchRunId


class DomainEventTests(unittest.TestCase):
    def test_event_is_deeply_immutable_and_round_trips(self) -> None:
        event = DomainEvent.create(
            event_type="research.run.started",
            occurred_at=Instant.parse("2026-08-03T04:00:00Z"),
            payload={"symbols": ["CN:600519", "US:AAPL"], "options": {"seed": 42}},
            event_id=EventId.parse("evt_12345678123456781234567812345678"),
            correlation_id=CorrelationId.parse("cor_12345678123456781234567812345678"),
            aggregate_id=ResearchRunId.parse("run_12345678123456781234567812345678"),
        )

        self.assertEqual(event.payload["symbols"], ("CN:600519", "US:AAPL"))
        with self.assertRaises(TypeError):
            event.payload["symbols"] = ()  # type: ignore[index]
        with self.assertRaises(TypeError):
            event.payload["options"]["seed"] = 7  # type: ignore[index]

        restored = DomainEvent.from_json(event.to_json())
        self.assertEqual(restored, event)
        self.assertEqual(restored.to_dict()["payload"]["options"]["seed"], 42)

    def test_invalid_event_name_and_payload_are_rejected(self) -> None:
        now = Instant.parse("2026-08-03T04:00:00Z")

        with self.assertRaises(ValueError):
            DomainEvent.create(event_type="Bad Event", occurred_at=now)
        with self.assertRaises(TypeError):
            DomainEvent.create(event_type="research.started", occurred_at=now, payload={"bad": object()})


if __name__ == "__main__":
    unittest.main()
