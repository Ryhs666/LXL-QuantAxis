"""Behavior tests for typed correlation identifiers."""

import unittest
from uuid import UUID

from src.lxl_quantaxis.core.ids import CorrelationId, EventId, IdentifierError, ResearchRunId


class IdentifierTests(unittest.TestCase):
    def test_ids_are_typed_and_deterministically_constructible(self) -> None:
        value = UUID("12345678-1234-5678-1234-567812345678")

        correlation_id = CorrelationId.new(lambda: value)
        event_id = EventId.new(lambda: value)
        run_id = ResearchRunId.new(lambda: value)

        self.assertEqual(str(correlation_id), "cor_12345678123456781234567812345678")
        self.assertEqual(str(event_id), "evt_12345678123456781234567812345678")
        self.assertEqual(str(run_id), "run_12345678123456781234567812345678")
        self.assertNotEqual(correlation_id, event_id)

    def test_parse_validates_type_prefix_and_uuid_payload(self) -> None:
        parsed = CorrelationId.parse("cor_12345678123456781234567812345678")

        self.assertEqual(str(parsed), "cor_12345678123456781234567812345678")
        with self.assertRaises(IdentifierError):
            CorrelationId.parse("evt_12345678123456781234567812345678")
        with self.assertRaises(IdentifierError):
            CorrelationId.parse("cor_not-a-uuid")

    def test_identifier_is_immutable(self) -> None:
        identifier = EventId.parse("evt_12345678123456781234567812345678")

        with self.assertRaises((AttributeError, TypeError)):
            identifier.value = "evt_00000000000000000000000000000000"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
