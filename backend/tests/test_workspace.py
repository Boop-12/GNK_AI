import pytest
from fastapi import HTTPException

from app import workspace
from app.config import Settings
from conftest import register


def authenticated(client):
    result = register(client)
    return {"Authorization": f"Bearer {result.json()['access_token']}", "Origin": "http://testserver"}


def test_workspace_requires_authentication(client):
    assert client.get("/api/v1/workspace/status").status_code == 401
    assert client.post("/api/v1/workspace/research", headers={"Origin": "http://testserver"},
                       json={"prompt": "Explain a research checklist", "consent": True}).status_code == 401


def test_status_is_read_only_and_redacts_provider_key(client, monkeypatch):
    monkeypatch.setattr(workspace, "get_settings", lambda: Settings(
        ai_enabled=True, openai_api_key="private-provider-key", openai_model="configured-model"))
    response = client.get("/api/v1/workspace/status", headers=authenticated(client))
    assert response.status_code == 200
    assert response.json()["liveExecutionEnabled"] is False
    assert response.json()["brokerVerified"] is False
    assert response.json()["ai"]["available"] is True
    assert "private-provider-key" not in response.text


def test_ai_disabled_never_calls_provider(client, monkeypatch):
    monkeypatch.setattr(workspace, "get_settings", lambda: Settings(ai_enabled=False))
    monkeypatch.setattr(workspace, "request_research", lambda *args: pytest.fail("Provider must not be called"))
    response = client.post("/api/v1/workspace/research", headers=authenticated(client),
                           json={"prompt": "Explain a research checklist", "consent": True})
    assert response.status_code == 503


def test_research_requires_origin_and_consent(client, monkeypatch):
    monkeypatch.setattr(workspace, "get_settings", lambda: Settings(
        ai_enabled=True, openai_api_key="private-key", openai_model="configured-model"))
    monkeypatch.setattr(workspace, "request_research", lambda *args: pytest.fail("Provider must not be called"))
    headers = authenticated(client)
    body = {"prompt": "Explain a research checklist", "consent": False}
    assert client.post("/api/v1/workspace/research", headers=headers, json=body).status_code == 422
    assert client.post("/api/v1/workspace/research", headers={**headers, "Origin": "https://other.test"},
                       json={**body, "consent": True}).status_code == 403


def test_research_rate_limit_prevents_provider_call(client, monkeypatch):
    monkeypatch.setattr(workspace, "get_settings", lambda: Settings(
        ai_enabled=True, openai_api_key="private-key", openai_model="configured-model"))
    def blocked(*args, **kwargs):
        raise HTTPException(status_code=429, detail="Too many requests")
    monkeypatch.setattr(workspace, "enforce_rate_limit", blocked)
    monkeypatch.setattr(workspace, "request_research", lambda *args: pytest.fail("Provider must not be called"))
    assert client.post("/api/v1/workspace/research", headers=authenticated(client),
                       json={"prompt": "Explain a research checklist", "consent": True}).status_code == 429


def test_provider_failure_is_sanitized(monkeypatch):
    from urllib.error import URLError
    def failed(*args, **kwargs):
        raise URLError("sensitive-provider-error")
    monkeypatch.setattr(workspace, "urlopen", failed)
    with pytest.raises(HTTPException) as error:
        workspace.request_research(Settings(openai_api_key="private-key", openai_model="test"), "test question")
    assert error.value.status_code == 502
    assert "sensitive" not in error.value.detail


def test_live_execution_flag_is_rejected():
    with pytest.raises(ValueError, match="Live execution is unavailable"):
        Settings(broker_trading_enabled=True)
