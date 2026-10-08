"""Read-only XTS credential verification; no keys or provider tokens are retained."""
import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

import redis
from fastapi import HTTPException

from app.rate_limit import _redis_client


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def verify_xts(base_url: str, api_key: str, api_secret: str) -> None:
    base = base_url.rstrip("/")
    endpoint = base + ("/auth/login" if base.endswith("/marketdata") else "/marketdata/auth/login")
    request = Request(endpoint, data=json.dumps({"appKey": api_key, "secretKey": api_secret,
                      "source": "WebAPI"}).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with build_opener(NoRedirect()).open(request, timeout=15) as response:
            raw = response.read(262145)
        if len(raw) > 262144:
            raise ValueError("Oversized response")
        data = json.loads(raw)
        result = data.get("result")
        if data.get("type") != "success" or not isinstance(result, dict) or not isinstance(result.get("token"), str) or not result["token"]:
            raise ValueError("Unverified login")
        # Verification only. Future quote streaming needs a separate session adapter.
    except (HTTPError, URLError, TimeoutError, ValueError, TypeError, AttributeError, OSError):
        raise HTTPException(status_code=502, detail="XTS could not verify these credentials. Check the market-data keys and ask your administrator to verify the XTS endpoint.") from None


def verification(user_id: int, broker_id: str):
    try:
        raw = _redis_client().get(f"broker-verification:{user_id}:{broker_id}")
        return json.loads(raw) if raw else None
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Broker verification temporarily unavailable") from None


def clear_verification(user_id: int, broker_id: str):
    try:
        _redis_client().delete(f"broker-verification:{user_id}:{broker_id}")
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Broker verification temporarily unavailable") from None


def record_verification(user_id: int, broker_id: str):
    value = {"verifiedAt": datetime.now(timezone.utc).isoformat()}
    try:
        _redis_client().setex(f"broker-verification:{user_id}:{broker_id}", 600, json.dumps(value))
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Broker verification could not be saved. Please try again.") from None
    return value
