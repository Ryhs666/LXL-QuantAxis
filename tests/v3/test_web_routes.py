"""Smoke test: all V3 web routes respond correctly."""
from __future__ import annotations

import pytest

from web_modern import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """Register a test user and return auth headers."""
    client.post("/api/register", json={
        "username": "routetest", "password": "test123456", "email": "rt@test.com",
    })
    resp = client.post("/api/login", json={
        "username": "routetest", "password": "test123456",
    })
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestPageRoutes:
    def test_workspace_page(self, client, auth_headers):
        r = client.get("/workspace", headers=auth_headers)
        assert r.status_code == 200
        assert b"Workspace" in r.data

    def test_journal_page(self, client, auth_headers):
        r = client.get("/journal", headers=auth_headers)
        assert r.status_code == 200
        assert b"Journal" in r.data or b"journal" in r.data


class TestWorkspaceAPI:
    def test_dashboard(self, client, auth_headers):
        r = client.get("/api/workspace/dashboard", headers=auth_headers)
        assert r.status_code == 200
        data = r.get_json()
        assert "stats" in data

    def test_watchlist_list(self, client, auth_headers):
        r = client.get("/api/workspace/watchlist", headers=auth_headers)
        assert r.status_code == 200

    def test_queue_list(self, client, auth_headers):
        r = client.get("/api/workspace/queue", headers=auth_headers)
        assert r.status_code == 200

    def test_theses_list(self, client, auth_headers):
        r = client.get("/api/workspace/theses", headers=auth_headers)
        assert r.status_code == 200

    def test_portfolio(self, client, auth_headers):
        r = client.get("/api/workspace/portfolio", headers=auth_headers)
        assert r.status_code == 200


class TestJournalAPI:
    def test_memory_list(self, client, auth_headers):
        r = client.get("/api/memory/list", headers=auth_headers)
        assert r.status_code == 200

    def test_memory_analytics(self, client, auth_headers):
        r = client.get("/api/memory/analytics", headers=auth_headers)
        assert r.status_code == 200
