from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.brokers.registry import broker_status, enabled_brokers
from app.config import get_settings
from app.dependencies import get_current_user
from app.models import User

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


@router.get("", response_model=list[BrokerStatusOut])
def list_broker_statuses(_: User = Depends(get_current_user)):
    settings = get_settings()
    return [broker_status(settings, item.identifier) for item in enabled_brokers(settings)]


@router.get("/{broker_id}/status", response_model=BrokerStatusOut)
def get_broker_status(broker_id: str, _: User = Depends(get_current_user)):
    status = broker_status(get_settings(), broker_id.lower())
    if status is None:
        raise HTTPException(status_code=404, detail="Broker is not enabled")
    return status
