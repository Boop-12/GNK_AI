from app.brokers.registry import broker_status, enabled_brokers
from app.config import Settings
from conftest import register


def test_xts_status_is_unconfigured_without_secrets():
    settings = Settings(valid_brokers="xts")
    status = broker_status(settings, "xts")
    assert status["status"] == "NOT_CONFIGURED"
    assert status["marketDataStatus"] == "NOT_CONFIGURED"
    assert status["tradingStatus"] == "NOT_CONFIGURED"
    assert "secret" not in str(status).lower()
    assert "token" not in str(status).lower()


def test_xts_market_and_trading_readiness_are_separate():
    settings = Settings(
        valid_brokers="xts",
        xts_market_data_base_url="https://market.example.test",
        xts_market_data_app_key="market-key",
        xts_market_data_secret_key="market-secret",
    )
    status = broker_status(settings, "xts")
    assert status["marketDataConfigured"] is True
    assert status["tradingConfigured"] is False
    assert status["marketDataStatus"] == "DISCONNECTED"
    assert status["tradingStatus"] == "NOT_CONFIGURED"


def test_unknown_broker_configuration_is_rejected():
    settings = Settings(valid_brokers="example-broker")
    try:
        enabled_brokers(settings)
    except ValueError as error:
        assert "unsupported broker" in str(error)
    else:
        raise AssertionError("Unsupported broker identifiers must not be accepted")


def test_valid_brokers_cannot_repeat_an_identifier():
    try:
        Settings(valid_brokers="xts, xts")
    except ValueError as error:
        assert "cannot contain duplicates" in str(error)
    else:
        raise AssertionError("Duplicate broker identifiers must be rejected")


def test_production_redirect_url_requires_https():
    try:
        Settings(app_env="production", redirect_url="http://www.gnkalgo.com/callback")
    except ValueError as error:
        assert "must use HTTPS" in str(error)
    else:
        raise AssertionError("Production callback URLs must use HTTPS")


def test_production_xts_hosts_require_https():
    try:
        Settings(app_env="production", xts_market_data_base_url="http://market.example.test")
    except ValueError as error:
        assert "must use HTTPS" in str(error)
    else:
        raise AssertionError("Production XTS hosts must use HTTPS")


def test_broker_status_requires_authentication(client):
    response = client.get("/api/v1/brokers")
    assert response.status_code == 401


def test_broker_status_endpoint_does_not_leak_credentials(client, monkeypatch):
    from app.brokers import routes

    settings = Settings(
        valid_brokers="xts",
        xts_market_data_base_url="https://market.example.test",
        xts_market_data_app_key="do-not-return-this-key",
        xts_market_data_secret_key="do-not-return-this-secret",
        xts_interactive_base_url="https://trade.example.test",
        xts_interactive_app_key="another-private-key",
        xts_interactive_secret_key="another-private-secret",
    )
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    created = register(client)
    headers = {"Authorization": f"Bearer {created.json()['access_token']}"}
    response = client.get("/api/v1/brokers", headers=headers)
    assert response.status_code == 200
    data = response.json()[0]
    assert data["broker"] == "xts"
    assert data["status"] == "DISCONNECTED"
    body = response.text
    for private_value in ("do-not-return-this-key", "do-not-return-this-secret", "another-private-key", "another-private-secret"):
        assert private_value not in body


def test_disabled_broker_cannot_be_queried(client, monkeypatch):
    from app.brokers import routes

    monkeypatch.setattr(routes, "get_settings", lambda: Settings(valid_brokers=""))
    created = register(client)
    headers = {"Authorization": f"Bearer {created.json()['access_token']}"}
    response = client.get("/api/v1/brokers/xts/status", headers=headers)
    assert response.status_code == 404
