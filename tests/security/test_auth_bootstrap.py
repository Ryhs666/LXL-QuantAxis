"""Security settings and one-time administrator bootstrap tests."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock

from src.auth.auth import create_admin_if_not_exists, verify_password
from src.lxl_quantaxis.core.security.rate_limit import InMemoryRateLimiter
from src.lxl_quantaxis.core.security.settings import (
    SecurityConfigurationError,
    SecuritySettings,
)

STRONG_SECRET = "jwt-secret-for-tests-with-more-than-32-characters"
STRONG_ADMIN_PASSWORD = "LocalAdmin2026Secure"


class SecuritySettingsTests(unittest.TestCase):
    def test_production_requires_explicit_jwt_secret(self) -> None:
        with self.assertRaisesRegex(
            SecurityConfigurationError,
            "JWT_SECRET_KEY is required",
        ):
            SecuritySettings.from_env({"LXL_ENV": "production"})

    def test_development_secret_is_random_and_loopback_is_default(self) -> None:
        first = SecuritySettings.from_env({})
        second = SecuritySettings.from_env({})

        self.assertTrue(first.jwt_secret_is_ephemeral)
        self.assertNotEqual(first.jwt_secret, second.jwt_secret)
        self.assertEqual(first.bind_host, "127.0.0.1")
        self.assertTrue(first.registration_enabled)

    def test_short_explicit_secret_is_rejected(self) -> None:
        with self.assertRaisesRegex(SecurityConfigurationError, "32 characters"):
            SecuritySettings.from_env({"JWT_SECRET_KEY": "too-short"})

    def test_production_secret_is_redacted_and_registration_is_closed(self) -> None:
        settings = SecuritySettings.from_env({"LXL_ENV": "production", "JWT_SECRET_KEY": STRONG_SECRET})

        self.assertNotIn(STRONG_SECRET, repr(settings))
        self.assertFalse(settings.jwt_secret_is_ephemeral)
        self.assertFalse(settings.registration_enabled)


class AdminBootstrapTests(unittest.TestCase):
    @staticmethod
    def _session(*query_results: object) -> Mock:
        session = Mock()
        session.query.return_value.filter_by.return_value.first.side_effect = query_results
        return session

    def test_development_without_password_does_not_create_admin(self) -> None:
        session = self._session(None)
        output = io.StringIO()

        with redirect_stdout(output):
            created = create_admin_if_not_exists(
                session_factory=Mock(return_value=session),
                environ={},
            )

        self.assertFalse(created)
        session.add.assert_not_called()
        self.assertIn("ADMIN_PASSWORD is required", output.getvalue())

    def test_production_without_bootstrap_password_fails_closed(self) -> None:
        session = self._session(None)

        with self.assertRaisesRegex(SecurityConfigurationError, "ADMIN_PASSWORD"):
            create_admin_if_not_exists(
                session_factory=Mock(return_value=session),
                environ={
                    "LXL_ENV": "production",
                    "JWT_SECRET_KEY": STRONG_SECRET,
                },
            )

        session.add.assert_not_called()

    def test_bootstrap_creates_admin_without_logging_password(self) -> None:
        session = self._session(None, None)
        output = io.StringIO()

        with redirect_stdout(output):
            created = create_admin_if_not_exists(
                session_factory=Mock(return_value=session),
                environ={"ADMIN_PASSWORD": STRONG_ADMIN_PASSWORD},
            )

        self.assertTrue(created)
        admin = session.add.call_args.args[0]
        self.assertEqual(admin.username, "admin")
        self.assertEqual(admin.role, "admin")
        self.assertTrue(verify_password(STRONG_ADMIN_PASSWORD, admin.password_hash))
        self.assertNotIn(STRONG_ADMIN_PASSWORD, output.getvalue())
        session.commit.assert_called_once()

    def test_existing_username_is_never_promoted_to_admin(self) -> None:
        existing_user = Mock(role="user")
        session = self._session(None, existing_user)

        with self.assertRaisesRegex(SecurityConfigurationError, "non-admin"):
            create_admin_if_not_exists(
                session_factory=Mock(return_value=session),
                environ={"ADMIN_PASSWORD": STRONG_ADMIN_PASSWORD},
            )

        self.assertEqual(existing_user.role, "user")
        session.add.assert_not_called()


class RateLimiterTests(unittest.TestCase):
    def test_sliding_window_blocks_and_recovers(self) -> None:
        now = [100.0]
        limiter = InMemoryRateLimiter(clock=lambda: now[0])

        self.assertTrue(limiter.check("login:user", limit=2, window_seconds=10).allowed)
        self.assertTrue(limiter.check("login:user", limit=2, window_seconds=10).allowed)
        blocked = limiter.check("login:user", limit=2, window_seconds=10)
        self.assertFalse(blocked.allowed)
        self.assertEqual(blocked.retry_after_seconds, 10)

        now[0] = 111.0
        self.assertTrue(limiter.check("login:user", limit=2, window_seconds=10).allowed)


if __name__ == "__main__":
    unittest.main()
