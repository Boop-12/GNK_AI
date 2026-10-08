import json
from urllib.parse import parse_qs, urlencode, urlparse

import pytest
from fastapi import HTTPException

from app.brokers import oauth
from app.config import Settings
from conftest import register


class StateStore:
    def __init__(self):
        self.values, self.now = {}, 0
    def setex(self, key, ttl, value):
        self.values[key] = (self.now + ttl, value)
    def get(self, key):
        saved = self.values.get(key)
        return saved[1] if saved and saved[0] > self.now else None
    def getdel(self, key):
        value = self.get(key)
        self.values.pop(key, None)
        return value


@pytest.fixture
def flow(client, monkeypatch):
    settings = Settings(valid_brokers="fyers", fyers_app_id="TESTAPP-100", fyers_app_secret="private-app-secret",
                        redirect_url="http://testserver" + oauth.CALLBACK_PATH)
    store, exchanges, verified = StateStore(), [], []
    monkeypatch.setattr(oauth, "get_settings", lambda: settings)
    monkeypatch.setattr(oauth, "_redis_client", lambda: store)
    monkeypatch.setattr(oauth, "enforce_rate_limit", lambda *a, **k: None)
    monkeypatch.setattr(oauth, "clear_verification", lambda *a: None)
    monkeypatch.setattr(oauth, "record_verification", lambda uid, bid: verified.append((uid, bid)))
    def exchange(settings, code):
        exchanges.append(code)
        return "private-provider-token"
    monkeypatch.setattr(oauth, "exchange_code", exchange)
    monkeypatch.setattr(oauth, "verify_profile", lambda *a: None)
    created = register(client)
    uid = created.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {created.json()['access_token']}", "Origin": "http://testserver"}
    return client, headers, store, exchanges, verified, settings, uid


def start_flow(flow):
    client, headers, *_ = flow
    response = client.post("/api/v1/brokers/fyers/oauth/start", headers=headers)
    assert response.status_code == 200
    assert "private-app-secret" not in response.text
    url = urlparse(response.json()["authorizationUrl"])
    assert url.hostname == "api-t1.fyers.in"
    params = parse_qs(url.query)
    assert params["redirect_uri"] == ["http://testserver" + oauth.CALLBACK_PATH]
    cookie = client.cookies.get(oauth.COOKIE_NAME)
    assert cookie and "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    return params["state"][0], cookie


def callback(client, state, code="private-code", **params):
    return client.get(oauth.CALLBACK_PATH + "?" + urlencode({"state": state, "auth_code": code, **params}), follow_redirects=False)


def test_callback_verifies_initiating_user_and_replay_cannot_exchange_twice(flow):
    client, _, store, exchanges, verified, _, uid = flow
    state, browser = start_flow(flow)
    assert "private-app-secret" not in str(store.values)
    result = callback(client, state)
    assert result.status_code == 303 and result.headers["location"] == "/dashboard"
    assert result.headers["cache-control"] == "no-store"
    assert exchanges == ["private-code"] and verified == [(uid, "fyers")]
    assert "private-code" not in result.text and "private-provider-token" not in result.text
    client.cookies.set(oauth.COOKIE_NAME, browser, domain="testserver.local", path=oauth.CALLBACK_PATH)
    repeat = callback(client, state)
    assert repeat.headers["location"] == "/broker?oauth=expired"
    assert len(exchanges) == 1


def test_other_browser_cannot_consume_authorization(flow):
    client, _, store, exchanges, verified, *_ = flow
    state, _ = start_flow(flow)
    client.cookies.clear()
    client.cookies.set(oauth.COOKIE_NAME, "another-browser", domain="testserver.local", path=oauth.CALLBACK_PATH)
    assert callback(client, state).headers["location"] == "/broker?oauth=expired"
    assert not exchanges and not verified and store.values


def test_expired_state_does_not_call_provider(flow):
    client, _, store, exchanges, _, *_ = flow
    state, _ = start_flow(flow)
    store.now = 601
    assert callback(client, state).headers["location"] == "/broker?oauth=expired"
    assert not exchanges


def test_cancelled_authorization_consumes_state_without_success(flow):
    client, _, store, exchanges, verified, *_ = flow
    state, _ = start_flow(flow)
    assert callback(client, state, error="access_denied").headers["location"] == "/broker?oauth=cancelled"
    assert not store.values and not exchanges and not verified


def test_provider_failure_never_sets_verification(flow, monkeypatch):
    client, _, _, exchanges, verified, *_ = flow
    state, _ = start_flow(flow)
    def fail(*a):
        raise HTTPException(status_code=502, detail="private-provider-error")
    monkeypatch.setattr(oauth, "verify_profile", fail)
    result = callback(client, state)
    assert result.headers["location"] == "/broker?oauth=failed"
    assert not verified and "private-provider-error" not in result.text


def test_start_requires_authentication_origin_and_exact_callback(flow, monkeypatch):
    client, headers, _, _, _, settings, _ = flow
    assert client.post("/api/v1/brokers/fyers/oauth/start", headers={"Origin": "http://testserver"}).status_code == 401
    assert client.post("/api/v1/brokers/fyers/oauth/start", headers={"Authorization": headers["Authorization"]}).status_code == 403
    settings.redirect_url = "https://wrong.example/callback"
    assert client.post("/api/v1/brokers/fyers/oauth/start", headers=headers).status_code == 503


def test_callback_query_is_redacted_from_asgi_scope(flow, monkeypatch):
    client, *_ = flow
    state, _ = start_flow(flow)
    seen = []
    def check(request, *a, **k):
        seen.append((request.scope["query_string"], request.state.oauth_query))
    monkeypatch.setattr(oauth, "enforce_rate_limit", check)
    result = callback(client, state)
    assert result.headers["location"] == "/dashboard"
    assert seen[0][0] == b"" and b"private-code" in seen[0][1]


def test_rotated_app_secret_invalidates_pending_authorization(flow):
    client, _, _, exchanges, _, settings, _ = flow
    state, _ = start_flow(flow)
    from pydantic import SecretStr
    settings.fyers_app_secret = SecretStr("rotated-secret")
    assert callback(client, state).headers["location"] == "/broker?oauth=expired"
    assert not exchanges


def test_exchange_uses_sha256_hash_and_never_accepts_error_body(monkeypatch):
    calls = []
    class Reply:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def read(self, size): return b'{"s":"error","message":"private-app-secret"}'
    class Opener:
        def open(self, request, timeout):
            calls.append(request)
            return Reply()
    monkeypatch.setattr(oauth, "build_opener", lambda *a: Opener())
    settings = Settings(fyers_app_id="TESTAPP-100", fyers_app_secret="private-app-secret")
    with pytest.raises(HTTPException) as failure:
        oauth.exchange_code(settings, "private-code")
    body = json.loads(calls[0].data)
    assert len(body["appIdHash"]) == 64
    assert "private-app-secret" not in calls[0].data.decode()
    assert "private-app-secret" not in failure.value.detail
