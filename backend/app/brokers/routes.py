from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, SecretStr

from app.brokers.registry import broker_status, enabled_brokers
from app.config import get_settings
from app.dependencies import get_current_user, require_same_origin
from app.models import User
from app.brokers.connection import clear_verification, record_verification, verification, verify_xts
from app.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/brokers", tags=["brokers"])


class BrokerStatusOut(BaseModel):
    broker: str
    name: str
    status: str
    marketDataStatus: str
    tradingStatus: str
    marketDataConfigured: bool
    tradingConfigured: bool
    redirectUrlConfigured: bool
    connectionAvailable: bool = False
    adminCredentialsAvailable: bool = False
    verifiedAt: str | None = None


def user_status(settings, broker_id, user):
    status = broker_status(settings, broker_id)
    if status is None:
        return None
    status["connectionAvailable"] = bool(settings.xts_market_data_base_url)
    status["adminCredentialsAvailable"] = any(role.name == "admin" for role in user.roles) and status["marketDataConfigured"]
    saved = verification(user.id, broker_id)
    if saved:
        status.update(status="VERIFIED", marketDataStatus="LOGIN_VERIFIED", verifiedAt=saved["verifiedAt"])
    return status


@router.get("", response_model=list[BrokerStatusOut])
def list_broker_statuses(user: User = Depends(get_current_user)):
    settings = get_settings()
    return [user_status(settings, item.identifier, user) for item in enabled_brokers(settings)]


@router.get("/{broker_id}/status", response_model=BrokerStatusOut)
def get_broker_status(broker_id: str, user: User = Depends(get_current_user)):
    status = user_status(get_settings(), broker_id.lower(), user)
    if status is None:
        raise HTTPException(status_code=404, detail="Broker is not enabled")
    return status


class ConnectIn(BaseModel):
    api_key: SecretStr = SecretStr("")
    api_secret: SecretStr = SecretStr("")
    use_server_credentials: bool = False


@router.post("/{broker_id}/connect", response_model=BrokerStatusOut, dependencies=[Depends(require_same_origin)])
def connect_broker(broker_id: str, data: ConnectIn, request: Request, user: User = Depends(get_current_user)):
    settings = get_settings()
    broker_id = broker_id.lower()
    if broker_id != "xts" or broker_status(settings, broker_id) is None:
        raise HTTPException(status_code=404, detail="Broker adapter is not available")
    if data.use_server_credentials and not any(role.name == "admin" for role in user.roles):
        raise HTTPException(status_code=403, detail="Only administrators can use server-configured credentials")
    if not settings.xts_market_data_base_url:
        raise HTTPException(status_code=503, detail="Your administrator must configure XTS_MARKET_DATA_BASE_URL before connecting")
    key = settings.xts_market_data_app_key if data.use_server_credentials else data.api_key.get_secret_value().strip()
    secret = settings.xts_market_data_secret_key.get_secret_value() if data.use_server_credentials else data.api_secret.get_secret_value()
    if not key or not secret or len(key) > 1024 or len(secret) > 1024:
        raise HTTPException(status_code=422, detail="Enter a valid API Key and API Secret")
    enforce_rate_limit(request, "broker-connect-ip", limit=20, window=600)
    enforce_rate_limit(request, "broker-connect-user", limit=5, window=600, subject=f"user-{user.id}")
    clear_verification(user.id, broker_id)
    verify_xts(settings.xts_market_data_base_url, key, secret)
    record_verification(user.id, broker_id)
    return user_status(settings, broker_id, user)
