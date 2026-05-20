from __future__ import annotations

from fastapi.testclient import TestClient

from ape.api import app


def test_sensitive_api_routes_require_configured_admin_token(monkeypatch):
    monkeypatch.delenv("APE_ADMIN_TOKEN", raising=False)
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    assert client.get("/config/intents").status_code == 503


def test_sensitive_api_routes_reject_bad_admin_token(monkeypatch):
    monkeypatch.setenv("APE_ADMIN_TOKEN", "correct-token")
    client = TestClient(app)

    resp = client.get("/admin/audit", headers={"X-APE-Admin-Token": "wrong-token"})
    assert resp.status_code == 401


def test_spa_routes_are_not_blocked_by_admin_token_middleware(monkeypatch):
    monkeypatch.setenv("APE_ADMIN_TOKEN", "correct-token")
    client = TestClient(app, raise_server_exceptions=False)

    assert client.get("/admin").status_code not in {401, 503}
    assert client.get("/analytics").status_code not in {401, 503}


def test_session_message_reads_require_user_id():
    client = TestClient(app)

    assert client.get("/sessions/sess_123/messages").status_code == 422
