"""Inspect Flask decorators without importing the side-effectful Web module."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WEB_MODULE = ROOT / "web_modern.py"


def _decorator_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _route_auth_matrix():
    tree = ast.parse(WEB_MODULE.read_text(encoding="utf-8"))
    result = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        decorators = {_decorator_name(item) for item in node.decorator_list}
        if "route" in decorators:
            result[node.name] = decorators & {"token_required", "admin_required"}
    return result


class TestLegacyWebAuthorization(unittest.TestCase):
    def test_known_protected_routes_keep_their_guards(self):
        matrix = _route_auth_matrix()
        expected = {
            "api_portfolio": "token_required",
            "api_backtest": "token_required",
            "api_admin_users": "admin_required",
            "api_game_trade": "token_required",
        }
        for function, guard in expected.items():
            with self.subTest(function=function):
                self.assertIn(guard, matrix[function])

    def test_sensitive_write_routes_require_authentication(self):
        """C-03 regression: every sensitive write route has an auth guard."""
        matrix = _route_auth_matrix()
        sensitive = (
            "api_metrics_update",
            "api_ai_chat",
            "api_ai_create_strategy",
            "api_factor_backtest",
            "api_database_migrate",
            "api_strategy_bank",
            "api_strategy_detail",
        )
        for function in sensitive:
            with self.subTest(function=function):
                self.assertTrue(
                    matrix[function] & {"token_required", "admin_required"},
                    f"{function} must declare an authentication guard",
                )


if __name__ == "__main__":
    unittest.main()
