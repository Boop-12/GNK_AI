from dataclasses import dataclass

from app.config import Settings


@dataclass(frozen=True)
class BrokerDefinition:
    identifier: str
    display_name: str


# Registry entries are only added when this application has a reviewed adapter.
BROKERS = {
    "xts": BrokerDefinition(identifier="xts", display_name="XTS"),
    "dhan": BrokerDefinition(identifier="dhan", display_name="Dhan"),
    "fyers": BrokerDefinition(identifier="fyers", display_name="Fyers"),
}


def enabled_brokers(settings: Settings) -> tuple[BrokerDefinition, ...]:
    identifiers = tuple(item for item in settings.valid_brokers.split(",") if item)
    unknown = set(identifiers) - BROKERS.keys()
    if unknown:
        raise ValueError(f"VALID_BROKERS contains unsupported broker(s): {', '.join(sorted(unknown))}")
    return tuple(BROKERS[item] for item in identifiers)


def validate_broker_settings(settings: Settings) -> None:
    enabled_brokers(settings)


def broker_status(settings: Settings, broker_id: str) -> dict:
    enabled = {broker.identifier for broker in enabled_brokers(settings)}
    definition = BROKERS.get(broker_id)
    if definition is None or broker_id not in enabled:
        return None

    if broker_id == "xts":
        market_ready = all((settings.xts_market_data_base_url,
                            settings.xts_market_data_app_key,
                            settings.xts_market_data_secret_key.get_secret_value()))
        trading_ready = all((settings.xts_interactive_base_url,
                             settings.xts_interactive_app_key,
                             settings.xts_interactive_secret_key.get_secret_value()))
        market_status = "DISCONNECTED" if market_ready else "NOT_CONFIGURED"
        trading_status = "DISCONNECTED" if trading_ready else "NOT_CONFIGURED"
    else:
        key, token = (settings.dhan_client_id, settings.dhan_access_token) if broker_id == "dhan" else (settings.fyers_app_id, settings.fyers_access_token)
        market_status = "DISCONNECTED" if key and token.get_secret_value() else "NOT_CONFIGURED"
        trading_status = "NOT_CONFIGURED"

    configured = market_status != "NOT_CONFIGURED" or trading_status != "NOT_CONFIGURED"
    return {
        "broker": definition.identifier,
        "name": definition.display_name,
        "status": "DISCONNECTED" if configured else "NOT_CONFIGURED",
        "marketDataStatus": market_status,
        "tradingStatus": trading_status,
        "marketDataConfigured": market_status != "NOT_CONFIGURED",
        "tradingConfigured": trading_status != "NOT_CONFIGURED",
        "redirectUrlConfigured": bool(settings.redirect_url),
    }
