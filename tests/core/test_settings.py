"""Behavior tests for typed V2 core settings."""

import json
import unittest

from src.lxl_quantaxis.core.config import CoreConfigurationError, CoreSettings, RuntimeEnvironment


class CoreSettingsTests(unittest.TestCase):
    def test_source_priority_is_explicit_then_environment_then_legacy(self) -> None:
        settings = CoreSettings.from_sources(
            legacy={
                "enabled": False,
                "environment": "development",
                "timezone": "Asia/Hong_Kong",
                "default_currency": "HKD",
            },
            environ={
                "V2_CORE_ENABLED": "true",
                "LXL_ENV": "test",
                "LXL_TIMEZONE": "UTC",
                "LXL_DEFAULT_CURRENCY": "USD",
            },
            overrides={"enabled": False, "default_currency": "CNY"},
        )

        self.assertFalse(settings.enabled)
        self.assertEqual(settings.environment, RuntimeEnvironment.TEST)
        self.assertEqual(settings.timezone_name, "UTC")
        self.assertEqual(settings.default_currency, "CNY")

    def test_defaults_keep_v2_disabled_for_safe_rollback(self) -> None:
        settings = CoreSettings.from_sources(environ={})

        self.assertFalse(settings.enabled)
        self.assertEqual(settings.environment, RuntimeEnvironment.DEVELOPMENT)
        self.assertEqual(settings.timezone_name, "Asia/Shanghai")
        self.assertEqual(settings.default_currency, "CNY")

    def test_settings_round_trip_through_json(self) -> None:
        original = CoreSettings.from_sources(
            environ={
                "V2_CORE_ENABLED": "yes",
                "LXL_ENV": "production",
                "LXL_TIMEZONE": "America/New_York",
                "LXL_DEFAULT_CURRENCY": "usd",
            }
        )

        restored = CoreSettings.from_json(original.to_json())

        self.assertEqual(restored, original)
        self.assertEqual(json.loads(original.to_json())["environment"], "production")

    def test_invalid_values_fail_closed(self) -> None:
        invalid_sources = [
            {"V2_CORE_ENABLED": "sometimes"},
            {"LXL_ENV": "staging"},
            {"LXL_TIMEZONE": "Mars/Olympus"},
            {"LXL_DEFAULT_CURRENCY": "RMB"},
        ]

        for environ in invalid_sources:
            with self.subTest(environ=environ), self.assertRaises(CoreConfigurationError):
                CoreSettings.from_sources(environ=environ)


if __name__ == "__main__":
    unittest.main()
