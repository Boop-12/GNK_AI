import time
from functools import lru_cache

import redis
from fastapi import HTTPException, Request

from app.config import get_settings

_local: dict[str, tuple[int, float]] = {}
_INCREMENT_WITH_TTL = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return count
"""


@lru_cache(maxsize=1)
def _redis_client():
    return redis.Redis.from_url(get_settings().redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)


def enforce_rate_limit(request: Request, action: str, limit: int = 10, window: int = 60, subject: str | None = None) -> None:
    # Key on endpoint and client address; never include passwords, tokens, or full email addresses.
    host = request.client.host if request.client else "unknown"
    key = f"auth:{action}:{subject if subject is not None else host}"
    settings = get_settings()
    try:
        client = _redis_client()
        count = int(client.eval(_INCREMENT_WITH_TTL, 1, key, window))
    except redis.RedisError:
        if settings.app_env == "production":
            raise HTTPException(status_code=503, detail="Authentication temporarily unavailable")
        count, expires = _local.get(key, (0, time.monotonic() + window))
        if time.monotonic() >= expires:
            count, expires = 0, time.monotonic() + window
        count += 1
        _local[key] = (count, expires)
    if count > limit:
        raise HTTPException(status_code=429, detail="Too many requests; try again later")
