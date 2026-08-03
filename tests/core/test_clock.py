"""Behavior tests for deterministic research time."""

import unittest
from datetime import timedelta

from src.lxl_quantaxis.core.clock import FrozenClock, FutureDataError, ResearchClock
from src.lxl_quantaxis.core.contracts import Instant


class ResearchClockTests(unittest.TestCase):
    def test_frozen_clock_is_deterministic_and_timezone_aware(self) -> None:
        source = FrozenClock(Instant.parse("2026-08-03T04:00:00Z"))
        clock = ResearchClock(source=source, timezone_name="Asia/Shanghai")

        self.assertEqual(clock.now().isoformat(), "2026-08-03T04:00:00Z")
        self.assertEqual(clock.local_now().isoformat(), "2026-08-03T12:00:00+08:00")

        source.advance(timedelta(hours=1))
        self.assertEqual(clock.now().isoformat(), "2026-08-03T05:00:00Z")

    def test_future_data_is_rejected(self) -> None:
        clock = ResearchClock.at("2026-08-03T04:00:00Z")

        clock.require_available(Instant.parse("2026-08-03T04:00:00Z"))
        with self.assertRaises(FutureDataError):
            clock.require_available(Instant.parse("2026-08-03T04:00:01Z"))


if __name__ == "__main__":
    unittest.main()
