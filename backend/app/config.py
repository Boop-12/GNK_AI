from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "production"
    app_name: str = "Gnk Algo API"
    frontend_url: str = "https://www.gnkalgo.com"
    cors_origins: str = ""
    database_url: str = "sqlite:///./gnkalgo.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: SecretStr = SecretStr("")
    jwt_issuer: str = "https://api.gnkalgo.com"
    jwt_audience: str = "gnkalgo-web"
    access_token_minutes: int = 10
    refresh_token_days: int = 14
    reset_token_minutes: int = 20
    valid_brokers: str = ""
    redirect_url: str = ""
    dhan_client_id: str = ""
    dhan_access_token: SecretStr = SecretStr("")
    fyers_app_id: str = ""
    fyers_access_token: SecretStr = SecretStr("")
    xts_market_data_base_url: str = ""
    xts_market_data_app_key: str = ""
    xts_market_data_secret_key: SecretStr = SecretStr("")
    xts_interactive_base_url: str = ""
    xts_interactive_app_key: str = ""
    xts_interactive_secret_key: SecretStr = SecretStr("")
    cookie_secure: bool = True
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = ""
    # This release has no live execution path. Enabling the flag is rejected.
    broker_trading_enabled: bool = False
    ai_enabled: bool = False
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = ""

    @field_validator("broker_trading_enabled")
    @classmethod
    def deny_live_execution(cls, value: bool) -> bool:
        if value:
            raise ValueError("Live execution is unavailable in this release; BROKER_TRADING_ENABLED must be false")
        return value

    @field_validator("jwt_secret_key")
    @classmethod
    def require_jwt_secret_in_production(cls, value: SecretStr, info):
        if info.data.get("app_env") == "production" and len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 characters in production")
        return value

    @field_validator("valid_brokers")
    @classmethod
    def validate_broker_list(cls, value: str) -> str:
        brokers = [item.strip().lower() for item in value.split(",") if item.strip()]
        if len(brokers) != len(set(brokers)):
            raise ValueError("VALID_BROKERS cannot contain duplicates")
        if any(not item.replace("-", "").isalnum() for item in brokers):
            raise ValueError("VALID_BROKERS must be comma-separated broker identifiers")
        return ",".join(brokers)

    @field_validator("redirect_url")
    @classmethod
    def validate_redirect_url(cls, value: str, info) -> str:
        value = value.strip()
        if not value:
            return value
        from urllib.parse import urlparse

        parsed = urlparse(value)
        if not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("REDIRECT_URL must be an absolute URL without credentials or a fragment")
        if info.data.get("app_env") == "production" and parsed.scheme != "https":
            raise ValueError("REDIRECT_URL must use HTTPS in production")
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("REDIRECT_URL must use HTTP or HTTPS")
        return value

    @field_validator("xts_market_data_base_url", "xts_interactive_base_url")
    @classmethod
    def validate_xts_base_url(cls, value: str, info) -> str:
        value = value.strip().rstrip("/")
        if not value:
            return value
        from urllib.parse import urlparse

        parsed = urlparse(value)
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError(f"{info.field_name.upper()} must be a base URL without credentials, query, or fragment")
        if parsed.scheme not in ({"https"} if info.data.get("app_env") == "production" else {"http", "https"}):
            raise ValueError(f"{info.field_name.upper()} must use HTTPS in production")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
