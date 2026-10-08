import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.config import get_settings

password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hash.verify(password, hashed)
    except Exception:
        return False


def opaque_token() -> str:
    return secrets.token_urlsafe(48)


def digest_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    secret = settings.jwt_secret_key.get_secret_value()
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be configured with at least 32 characters")
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user_id), "iss": settings.jwt_issuer, "aud": settings.jwt_audience,
              "iat": now, "nbf": now, "exp": now + timedelta(minutes=settings.access_token_minutes),
              "jti": secrets.token_urlsafe(16), "typ": "access"}
    return jwt.encode(claims, secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    settings = get_settings()
    claims = jwt.decode(token, settings.jwt_secret_key.get_secret_value(), algorithms=[ALGORITHM],
                        issuer=settings.jwt_issuer, audience=settings.jwt_audience,
                        options={"require": ["sub", "iss", "aud", "iat", "nbf", "exp", "jti", "typ"]})
    if claims.get("typ") != "access":
        raise jwt.InvalidTokenError("Wrong token type")
    return int(claims["sub"])
