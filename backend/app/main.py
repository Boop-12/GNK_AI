from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.brokers.registry import validate_broker_settings
from app.brokers.routes import router as brokers_router
from app.auth import router as auth_router
from app.config import get_settings
from app.users import router as users_router
from app.workspace import router as workspace_router

settings = get_settings()
if settings.app_env == "production":
    from urllib.parse import urlparse
    if not settings.cookie_secure or urlparse(settings.frontend_url).scheme != "https":
        raise ValueError("Production requires COOKIE_SECURE=true and an HTTPS FRONTEND_URL")
    if not settings.database_url.startswith("postgresql"):
        raise ValueError("Production requires PostgreSQL")
validate_broker_settings(settings)
app = FastAPI(title=settings.app_name, docs_url="/docs" if settings.app_env != "production" else None,
              redoc_url=None, openapi_url="/openapi.json" if settings.app_env != "production" else None)
app.state.frontend_origin = settings.frontend_url
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()] or [settings.frontend_url]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True,
                   allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(brokers_router, prefix="/api/v1")
app.include_router(workspace_router, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
async def sanitized_validation_error(request, exc: RequestValidationError):
    # Pydantic errors may include submitted input; never echo back credentials.
    errors = [{"loc": error.get("loc", ()), "msg": error.get("msg", "Invalid value"),
               "type": error.get("type", "value_error")} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.app_env == "production" and request.headers.get("x-forwarded-proto") == "https":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.get("/healthz", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
def readiness():
    from sqlalchemy import text
    from app.db import engine
    from app.rate_limit import _redis_client
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            connection.execute(text("SELECT id FROM users LIMIT 0"))
        _redis_client().ping()
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}
