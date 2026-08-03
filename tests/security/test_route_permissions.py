"""Static permission-matrix tests for side-effectful Flask routes."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB_MODULE = ROOT / "web_modern.py"


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _functions() -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(WEB_MODULE.read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


class RoutePermissionTests(unittest.TestCase):
    def test_sensitive_routes_have_least_privilege_guards(self) -> None:
        functions = _functions()
        expected = {
            "api_metrics_update": "admin_required",
            "api_ai_recommend_chat": "token_required",
            "api_ai_chat": "token_required",
            "api_ai_review": "token_required",
            "api_ai_market": "token_required",
            "api_ai_create_strategy": "token_required",
            "api_factor_backtest": "token_required",
            "api_database_status": "token_required",
            "api_database_migrate": "admin_required",
            "api_strategy_bank": "token_required",
            "api_strategy_detail": "token_required",
        }

        for function_name, required_guard in expected.items():
            with self.subTest(function=function_name):
                decorators = {_decorator_name(item) for item in functions[function_name].decorator_list}
                self.assertIn(required_guard, decorators)

    def test_public_auth_routes_are_rate_limited(self) -> None:
        functions = _functions()
        for function_name in ("api_register", "api_login"):
            with self.subTest(function=function_name):
                decorators = {_decorator_name(item) for item in functions[function_name].decorator_list}
                self.assertIn("auth_rate_limited", decorators)

    def test_database_migration_is_post_only(self) -> None:
        route = next(
            item for item in _functions()["api_database_migrate"].decorator_list if _decorator_name(item) == "route"
        )
        self.assertIsInstance(route, ast.Call)
        methods_keyword = next(keyword for keyword in route.keywords if keyword.arg == "methods")
        methods = {item.value for item in methods_keyword.value.elts if isinstance(item, ast.Constant)}
        self.assertEqual(methods, {"POST"})

    def test_strategy_routes_bind_storage_to_authenticated_owner(self) -> None:
        source = WEB_MODULE.read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count("owner_id=g.user_id"), 5)

    def test_web_server_uses_security_bind_host(self) -> None:
        source = WEB_MODULE.read_text(encoding="utf-8")
        self.assertIn("bind_host = SECURITY_SETTINGS.bind_host", source)
        self.assertIn("app.run(host=bind_host", source)


if __name__ == "__main__":
    unittest.main()
