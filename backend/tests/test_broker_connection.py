from fastapi import HTTPException
import pytest
from app.brokers import routes
from app.brokers.connection import verify_xts
from app.config import Settings
from conftest import register
from app.brokers.connection import verify_profile


@pytest.fixture
def connection(client, monkeypatch):
    monkeypatch.setattr(routes, "get_settings", lambda: Settings(valid_brokers="xts", xts_market_data_base_url="https://broker.example.test"))
    monkeypatch.setattr(routes, "enforce_rate_limit", lambda *a, **k: None)
    saved = {}
    monkeypatch.setattr(routes, "clear_verification", lambda uid, bid: saved.pop((uid, bid), None))
    monkeypatch.setattr(routes, "record_verification", lambda uid, bid: saved.update({(uid, bid): {"verifiedAt": "2026-10-08T12:00:00+00:00"}}))
    monkeypatch.setattr(routes, "verification", lambda uid, bid: saved.get((uid, bid)))
    created = register(client)
    return client, {"Authorization": f"Bearer {created.json()['access_token']}", "Origin": "http://testserver"}, saved


def test_success_is_user_scoped_and_does_not_return_credentials(connection, monkeypatch):
    client, headers, saved = connection
    calls = []
    monkeypatch.setattr(routes, "verify_xts", lambda *args: calls.append(args))
    result = client.post("/api/v1/brokers/xts/connect", headers=headers, json={"api_key": "private-key", "api_secret": "private-secret"})
    assert result.status_code == 200 and result.json()["status"] == "VERIFIED"
    assert len(calls) == 1
    assert "private-key" not in result.text and "private-secret" not in result.text
    other = register(client, "other@example.com")
    response = client.get("/api/v1/brokers", headers={"Authorization": f"Bearer {other.json()['access_token']}"})
    assert response.json()[0]["status"] != "VERIFIED"


def test_failed_login_clears_previous_verification(connection, monkeypatch):
    client, headers, saved = connection
    saved[(1, "xts")] = {"verifiedAt": "old"}
    def fail(*args):
        raise HTTPException(status_code=502, detail="Broker rejected credentials")
    monkeypatch.setattr(routes, "verify_xts", fail)
    result = client.post("/api/v1/brokers/xts/connect", headers=headers, json={"api_key": "key", "api_secret": "secret"})
    assert result.status_code == 502 and not saved


def test_non_admin_cannot_use_server_credentials(connection):
    client, headers, _ = connection
    assert client.post("/api/v1/brokers/xts/connect", headers=headers, json={"use_server_credentials": True}).status_code == 403


def test_requires_origin_and_supported_broker(connection):
    client, headers, _ = connection
    assert client.post("/api/v1/brokers/xts/connect", headers={"Authorization": headers["Authorization"]}, json={}).status_code == 403
    assert client.post("/api/v1/brokers/dhan/connect", headers=headers, json={}).status_code == 404


def test_provider_error_with_http_200_is_rejected_and_redacted(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size): return b'{"type":"error","description":"private-secret"}'
    class Opener:
        def open(self, request, timeout): return Response()
    monkeypatch.setattr("app.brokers.connection.build_opener", lambda *a: Opener())
    with pytest.raises(HTTPException) as error:
        verify_xts("https://broker.example.test", "private-key", "private-secret")
    assert error.value.status_code == 502 and "private-secret" not in error.value.detail


@pytest.mark.parametrize("broker,payload", [
    ("dhan", b'{"dhanClientId":"12345","tokenValidity":"09/10/2026 15:37"}'),
    ("fyers", b'{"s":"ok","code":200,"data":{"fy_id":"AB12345"}}'),
])
def test_profile_verification_uses_fixed_get_endpoint_and_private_header(monkeypatch, broker, payload):
    calls = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size): return payload
    class Opener:
        def open(self, request, timeout):
            calls.append(request)
            return Response()
    monkeypatch.setattr("app.brokers.connection.build_opener", lambda *a: Opener())
    verify_profile(broker, "12345", "private-token")
    assert calls[0].get_method() == "GET"
    assert calls[0].full_url in {"https://api.dhan.co/v2/profile", "https://api-t1.fyers.in/api/v3/profile"}
    assert "private-token" not in calls[0].full_url


def test_dhan_client_id_must_match_verified_profile(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size): return b'{"dhanClientId":"someone-else","tokenValidity":"valid"}'
    class Opener:
        def open(self, request, timeout): return Response()
    monkeypatch.setattr("app.brokers.connection.build_opener", lambda *a: Opener())
    with pytest.raises(HTTPException):
        verify_profile("dhan", "12345", "private-token")


@pytest.mark.parametrize("broker", ["dhan", "fyers"])
def test_token_broker_connect_success(connection, monkeypatch, broker):
    client, headers, _ = connection
    monkeypatch.setattr(routes, "get_settings", lambda: Settings(valid_brokers="dhan,fyers"))
    monkeypatch.setattr(routes, "verify_profile", lambda *a: None)
    result = client.post(f"/api/v1/brokers/{broker}/connect", headers=headers, json={"api_key": "12345", "api_secret": "private-token"})
    assert result.status_code == 200 and result.json()["status"] == "VERIFIED"
    assert "private-token" not in result.text
