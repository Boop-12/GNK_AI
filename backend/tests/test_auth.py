from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select

from app.config import get_settings
from app.db import get_db
from app.models import Authority, PasswordReset, RefreshToken, Role, User, now_utc
from app.security import digest_token, opaque_token

ORIGIN = {"origin": "http://testserver"}


def register(client, email="sam@example.com"):
    return client.post("/api/v1/auth/register", headers=ORIGIN, json={
        "name": "Sam User", "email": email, "password": "Strong!Password42"
    })


def test_registration_and_password_hash(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "sam@example.com"
    assert "password" not in body and "password_hash" not in body
    assert response.headers.get("set-cookie").startswith("gnk_refresh=")
    db = next(client.app.dependency_overrides[get_db]())
    user = db.scalar(select(User).where(User.email == "sam@example.com"))
    assert user.password_hash != "Strong!Password42"
    assert user.roles[0].name == "user"
    db.close()


def test_duplicate_registration_is_rejected(client):
    assert register(client).status_code == 201
    response = register(client)
    assert response.status_code == 409
    assert "email" not in response.json()["detail"].lower()


def test_password_policy(client):
    response = client.post("/api/v1/auth/register", headers=ORIGIN, json={"name":"x","email":"x@example.com","password":"short"})
    assert response.status_code == 422
    assert "short" not in response.text


def test_login_success_and_failure(client):
    register(client)
    result = client.post("/api/v1/auth/login", headers=ORIGIN, json={"email":"SAM@example.com","password":"Strong!Password42"})
    assert result.status_code == 200
    assert result.json()["access_token"]
    failed = client.post("/api/v1/auth/login", headers=ORIGIN, json={"email":"sam@example.com","password":"wrong-password"})
    assert failed.status_code == 401
    assert failed.json()["detail"] == "Invalid email or password"


def test_jwt_invalid_and_expired_are_rejected(client):
    register(client)
    invalid = client.get("/api/v1/users/me", headers={"Authorization":"Bearer nope"})
    assert invalid.status_code == 401
    settings = get_settings()
    expired = jwt.encode({"sub":"1","iss":settings.jwt_issuer,"aud":settings.jwt_audience,
                          "iat":datetime.now(timezone.utc)-timedelta(minutes=5),
                          "nbf":datetime.now(timezone.utc)-timedelta(minutes=5),
                          "exp":datetime.now(timezone.utc)-timedelta(minutes=1),"jti":"expired","typ":"access"},
                         settings.jwt_secret_key.get_secret_value(), algorithm="HS256")
    response = client.get("/api/v1/users/me", headers={"Authorization":f"Bearer {expired}"})
    assert response.status_code == 401


def test_protected_route_and_authority_check(client):
    assert client.get("/api/v1/users/me").status_code == 401
    created = register(client)
    token = created.json()["access_token"]
    me = client.get("/api/v1/users/me", headers={"Authorization":f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == "sam@example.com"
    assert client.get("/api/v1/admin/users", headers={"Authorization":f"Bearer {token}"}).status_code == 403
    db = next(client.app.dependency_overrides[get_db]())
    user = db.scalar(select(User).where(User.email == "sam@example.com"))
    role = user.roles[0]
    authority = Authority(name="users:read")
    role.authorities.append(authority)
    db.commit()
    db.close()
    allowed = client.get("/api/v1/admin/users", headers={"Authorization":f"Bearer {token}"})
    assert allowed.status_code == 200


def test_refresh_rotates_cookie_and_logout_revokes(client):
    result = register(client)
    original = result.json()["access_token"]
    refreshed = client.post("/api/v1/auth/refresh", headers=ORIGIN)
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"] != original
    assert "gnk_refresh=" in refreshed.headers["set-cookie"]
    logged_out = client.post("/api/v1/auth/logout", headers=ORIGIN)
    assert logged_out.status_code == 204
    assert client.post("/api/v1/auth/refresh", headers=ORIGIN).status_code == 401


def test_refresh_reuse_revokes_remaining_sessions(client):
    register(client)
    first = client.cookies.get("gnk_refresh")
    client.post("/api/v1/auth/refresh", headers=ORIGIN)
    # Replay the rotated token; the server must invalidate all sessions for the account.
    response = client.post("/api/v1/auth/refresh", headers=ORIGIN, cookies={"gnk_refresh":first})
    assert response.status_code == 401
    assert client.post("/api/v1/auth/refresh", headers=ORIGIN).status_code == 401


def test_forgot_password_is_enumeration_safe_and_reset_is_single_use(client, monkeypatch):
    register(client)
    captured = {}
    monkeypatch.setattr("app.auth.send_reset_email", lambda email, token: captured.update(email=email, token=token))
    known = client.post("/api/v1/auth/forgot-password", headers=ORIGIN, json={"email":"sam@example.com"})
    unknown = client.post("/api/v1/auth/forgot-password", headers=ORIGIN, json={"email":"nobody@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    reset = client.post("/api/v1/auth/reset-password", headers=ORIGIN,
                        json={"token":captured["token"],"new_password":"AnEvenStronger!Password43"})
    assert reset.status_code == 204
    reused = client.post("/api/v1/auth/reset-password", headers=ORIGIN,
                         json={"token":captured["token"],"new_password":"AnotherStrong!Password44"})
    assert reused.status_code == 400
    login = client.post("/api/v1/auth/login", headers=ORIGIN,
                        json={"email":"sam@example.com","password":"AnEvenStronger!Password43"})
    assert login.status_code == 200


def test_expired_reset_token_rejected(client):
    register(client)
    db = next(client.app.dependency_overrides[get_db]())
    user = db.scalar(select(User).where(User.email == "sam@example.com"))
    raw = opaque_token()
    db.add(PasswordReset(user_id=user.id, token_hash=digest_token(raw), expires_at=now_utc()-timedelta(seconds=1)))
    db.commit()
    db.close()
    response = client.post("/api/v1/auth/reset-password", headers=ORIGIN,
                           json={"token":raw,"new_password":"AnEvenStronger!Password43"})
    assert response.status_code == 400


def test_cookie_endpoints_require_same_origin(client):
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 403
