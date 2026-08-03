"""Behavioral authentication and role-matrix tests."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flask import Flask, g, jsonify

from src.auth import admin_required, generate_token, token_required


class AuthDecoratorTests(unittest.TestCase):
    def setUp(self) -> None:
        app = Flask(__name__)

        @app.get("/protected")
        @token_required
        def protected():
            return jsonify({"user_id": g.user_id})

        @app.get("/admin")
        @admin_required
        def admin():
            return jsonify({"role": g.user_role})

        self.client = app.test_client()

    @staticmethod
    def _session_for(user: object) -> Mock:
        session = Mock()
        session.query.return_value.filter_by.return_value.first.return_value = user
        return session

    def test_anonymous_request_is_rejected(self) -> None:
        response = self.client.get("/protected")
        self.assertEqual(response.status_code, 401)

    def test_active_user_can_access_authenticated_route(self) -> None:
        user = SimpleNamespace(id=7, role="user", is_active=True)
        session = self._session_for(user)

        with patch("src.database.SessionLocal", return_value=session):
            response = self.client.get(
                "/protected",
                headers={"Authorization": f"Bearer {generate_token(7)}"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["user_id"], 7)

    def test_disabled_user_is_rejected_even_with_valid_token(self) -> None:
        user = SimpleNamespace(id=7, role="user", is_active=False)
        session = self._session_for(user)

        with patch("src.database.SessionLocal", return_value=session):
            response = self.client.get(
                "/protected",
                headers={"Authorization": f"Bearer {generate_token(7)}"},
            )

        self.assertEqual(response.status_code, 401)

    def test_regular_user_cannot_access_admin_route(self) -> None:
        user = SimpleNamespace(id=7, role="user", is_active=True)
        session = self._session_for(user)

        with patch("src.database.SessionLocal", return_value=session):
            response = self.client.get(
                "/admin",
                headers={"Authorization": f"Bearer {generate_token(7)}"},
            )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_admin_route(self) -> None:
        user = SimpleNamespace(id=1, role="admin", is_active=True)
        session = self._session_for(user)

        with patch("src.database.SessionLocal", return_value=session):
            response = self.client.get(
                "/admin",
                headers={"Authorization": f"Bearer {generate_token(1)}"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["role"], "admin")


if __name__ == "__main__":
    unittest.main()
