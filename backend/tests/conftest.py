import os
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-with-at-least-32-chars")
os.environ.setdefault("JWT_ISSUER", "https://test.gnkalgo.com")
os.environ.setdefault("JWT_AUDIENCE", "gnkalgo-test")
os.environ.setdefault("FRONTEND_URL", "http://testserver")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.rate_limit import enforce_rate_limit


@pytest.fixture
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr("app.auth.enforce_rate_limit", lambda *a, **k: None)
    monkeypatch.setattr("app.auth.send_reset_email", lambda *a, **k: None)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def register(client, email="sam@example.com"):
    return client.post("/api/v1/auth/register", headers={"origin": "http://testserver"}, json={
        "name": "Sam User", "email": email, "password": "Strong!Password42"
    })
