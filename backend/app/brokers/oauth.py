"""FYERS authorization: browser-bound, user-bound, single-use state; no token storage."""
import hashlib
import hmac
import json
import secrets
from urllib.parse import parse_qs, urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request as ProviderRequest, build_opener

import redis
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.brokers.connection import NoRedirect, clear_verification, record_verification, verify_profile
from app.config import get_settings
from app.db import get_db
from app.dependencies import get_current_user, require_same_origin
from app.models import User
from app.rate_limit import _redis_client, enforce_rate_limit

router = APIRouter(prefix="/brokers/fyers/oauth", tags=["brokers"])
CALLBACK_PATH = "/api/v1/brokers/fyers/oauth/callback"
COOKIE_NAME = "gnk_fyers_oauth"
TTL = 600
USER_AGENT = "Mozilla/5.0 (compatible; GNKALGO/1.0)"


def fingerprint(settings):
    return hashlib.sha256(f"{settings.fyers_app_id}:{settings.fyers_app_secret.get_secret_value()}:{settings.redirect_url}".encode()).hexdigest()


def oauth_ready(settings):
    return ("fyers" in settings.valid_brokers.split(",") and bool(settings.fyers_app_id.strip())
            and bool(settings.fyers_app_secret.get_secret_value())
            and settings.redirect_url == settings.frontend_url.rstrip("/") + CALLBACK_PATH)


def exchange_code(settings, code):
    app_hash = hashlib.sha256(f"{settings.fyers_app_id}:{settings.fyers_app_secret.get_secret_value()}".encode()).hexdigest()
    payload = {"grant_type": "authorization_code", "appIdHash": app_hash, "code": code}
    request = ProviderRequest("https://api-t1.fyers.in/api/v3/validate-authcode", data=json.dumps(payload).encode(),
                              headers={"Content-Type": "application/json", "User-Agent": USER_AGENT}, method="POST")
    try:
        with build_opener(NoRedirect()).open(request, timeout=15) as response:
            raw = response.read(262145)
        if len(raw) > 262144:
            raise ValueError("Oversized response")
        result = json.loads(raw)
        token = result.get("access_token")
        if result.get("s") != "ok" or not isinstance(token, str) or not token or len(token) > 8192 or any(ch in token for ch in "\r\n"):
            raise ValueError("Token exchange rejected")
        return token
    except (HTTPError, URLError, TimeoutError, ValueError, TypeError, AttributeError, OSError):
        raise HTTPException(status_code=502, detail="FYERS authorization could not be verified") from None


@router.post("/start", dependencies=[Depends(require_same_origin)])
def start(request: Request, response: Response, user: User = Depends(get_current_user)):
    settings = get_settings()
    if not oauth_ready(settings):
        raise HTTPException(status_code=503, detail="Your administrator needs to configure FYERS App ID, App Secret and the registered callback URL")
    enforce_rate_limit(request, "fyers-oauth-start", limit=5, window=600, subject=f"user-{user.id}")
    state, browser = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    value = {"userId": user.id, "browserHash": hashlib.sha256(browser.encode()).hexdigest(), "appFingerprint": fingerprint(settings)}
    try:
        _redis_client().setex("fyers-oauth:" + hashlib.sha256(state.encode()).hexdigest(), TTL, json.dumps(value))
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Broker authorization temporarily unavailable") from None
    clear_verification(user.id, "fyers")
    response.set_cookie(COOKIE_NAME, browser, max_age=TTL, secure=settings.cookie_secure, httponly=True,
                        samesite="lax", path=CALLBACK_PATH)
    response.headers["Cache-Control"] = "no-store"
    return {"authorizationUrl": "https://api-t1.fyers.in/api/v3/generate-authcode?" + urlencode({
        "client_id": settings.fyers_app_id, "redirect_uri": settings.redirect_url,
        "response_type": "code", "state": state})}


def callback_response(settings, outcome):
    response = RedirectResponse("/dashboard" if outcome == "success" else "/broker?oauth=" + outcome, status_code=303,
                                headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
    response.delete_cookie(COOKIE_NAME, path=CALLBACK_PATH, secure=settings.cookie_secure, httponly=True, samesite="lax")
    return response


@router.get("/callback")
def callback(request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    # main.py removes the query from ASGI scope before access logging can see it.
    query = getattr(request.state, "oauth_query", b"")
    try:
        if len(query) > 16384:
            raise ValueError("Invalid query")
        params = parse_qs(query.decode("utf-8"), keep_blank_values=True, max_num_fields=8)
        state_values, code_values = params.get("state", []), params.get("auth_code", [])
        browser = request.cookies.get(COOKIE_NAME, "")
        if not oauth_ready(settings) or len(state_values) != 1 or len(state_values[0]) > 128 or not state_values[0] or not browser or len(browser) > 128:
            return callback_response(settings, "expired")
        enforce_rate_limit(request, "fyers-oauth-callback", limit=30, window=600)
        key = "fyers-oauth:" + hashlib.sha256(state_values[0].encode()).hexdigest()
        client = _redis_client()
        raw = client.get(key)
        if not raw:
            return callback_response(settings, "expired")
        saved = json.loads(raw)
        if not hmac.compare_digest(saved["browserHash"], hashlib.sha256(browser.encode()).hexdigest()):
            return callback_response(settings, "expired")
        # GETDEL is atomic: a concurrent or repeated callback cannot exchange twice.
        if client.getdel(key) != raw or saved["appFingerprint"] != fingerprint(settings):
            return callback_response(settings, "expired")
        user = db.get(User, saved["userId"])
        if not user or not user.is_active:
            return callback_response(settings, "expired")
        if params.get("error") or params.get("s", ["ok"]) != ["ok"] or len(code_values) != 1 or not code_values[0] or len(code_values[0]) > 8192:
            return callback_response(settings, "cancelled")
        token = exchange_code(settings, code_values[0])
        verify_profile("fyers", settings.fyers_app_id, token)
        record_verification(user.id, "fyers")
        return callback_response(settings, "success")
    except (redis.RedisError, HTTPException, ValueError, KeyError, TypeError, UnicodeError):
        # Never return authorization codes, tokens, app secrets or provider bodies.
        return callback_response(settings, "failed")
