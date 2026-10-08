from datetime import datetime, timedelta, timezone
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.dependencies import get_current_user, require_same_origin
from app.mailer import send_reset_email
from app.models import Authority, PasswordReset, RefreshToken, Role, User, now_utc
from app.rate_limit import enforce_rate_limit
from app.schemas import AuthOut, EmailIn, LoginIn, RegisterIn, ResetPasswordIn, UserOut
from app.security import create_access_token, digest_token, hash_password, opaque_token, verify_password

router = APIRouter(prefix="/auth", tags=["authentication"])
REFRESH_COOKIE = "gnk_refresh"
_DUMMY_PASSWORD_HASH = hash_password("constant-time-dummy-password")
logger = logging.getLogger(__name__)


def expired_at(value: datetime, now: datetime) -> bool:
    # SQLite drops timezone metadata for DateTime(timezone=True); persisted values are UTC.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value <= now


def as_user(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email,
                   roles=[role.name for role in user.roles],
                   authorities=sorted({p.name for role in user.roles for p in role.authorities}))


def set_refresh_cookie(response: Response, raw: str) -> None:
    settings = get_settings()
    response.set_cookie(REFRESH_COOKIE, raw, max_age=settings.refresh_token_days * 86400,
                        httponly=True, secure=settings.cookie_secure, samesite="lax", path="/api/v1/auth")


def issue_refresh(db: Session, user: User) -> str:
    raw = opaque_token()
    db.add(RefreshToken(user_id=user.id, token_hash=digest_token(raw),
                        expires_at=now_utc() + timedelta(days=get_settings().refresh_token_days)))
    return raw


def invalidate_user_refreshes(db: Session, user_id: int) -> None:
    for item in db.scalars(select(RefreshToken).where(RefreshToken.user_id == user_id,
                                      RefreshToken.revoked_at.is_(None))):
        item.revoked_at = now_utc()


def deliver_reset_email(email: str, raw: str) -> None:
    try:
        send_reset_email(email, raw)
    except Exception:
        # Log only a generic event: SMTP exceptions can include recipient/server details.
        logger.warning("Password reset email delivery failed")


@router.post("/register", response_model=AuthOut, status_code=201, dependencies=[Depends(require_same_origin)])
def register(data: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    enforce_rate_limit(request, "register", limit=5)
    if db.scalar(select(User.id).where(User.email == data.email)):
        raise HTTPException(status_code=409, detail="Unable to create account with those details")
    role = db.scalar(select(Role).where(Role.name == "user"))
    if role is None:
        role = Role(name="user")
        db.add(role)
        db.flush()
    user = User(name=data.name, email=data.email, password_hash=hash_password(data.password), roles=[role])
    db.add(user)
    try:
        db.flush()
        refresh = issue_refresh(db, user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Unable to create account with those details") from None
    set_refresh_cookie(response, refresh)
    return AuthOut(access_token=create_access_token(user.id), user=as_user(user))


@router.post("/login", response_model=AuthOut, dependencies=[Depends(require_same_origin)])
def login(data: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    enforce_rate_limit(request, "login", limit=10)
    user = db.scalar(select(User).where(User.email == data.email))
    # Verify against a fixed dummy Argon2 hash for unknown users to reduce timing-based enumeration.
    valid = verify_password(data.password, user.password_hash if user else _DUMMY_PASSWORD_HASH)
    if not user or not user.is_active or not valid:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    raw = issue_refresh(db, user)
    db.commit()
    set_refresh_cookie(response, raw)
    return AuthOut(access_token=create_access_token(user.id), user=as_user(user))


@router.post("/refresh", response_model=AuthOut, dependencies=[Depends(require_same_origin)])
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    enforce_rate_limit(request, "refresh", limit=20)
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="Refresh session is not valid")
    token_hash = digest_token(raw)
    item = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update())
    now = now_utc()
    if not item or expired_at(item.expires_at, now):
        response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth", secure=get_settings().cookie_secure,
                               httponly=True, samesite="lax")
        raise HTTPException(status_code=401, detail="Refresh session is not valid")
    if item.revoked_at:
        # A previously rotated credential has been replayed: revoke all sessions for this user.
        invalidate_user_refreshes(db, item.user_id)
        db.commit()
        response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth", secure=get_settings().cookie_secure,
                               httponly=True, samesite="lax")
        raise HTTPException(status_code=401, detail="Refresh session is not valid")
    user = db.get(User, item.user_id)
    if not user or not user.is_active:
        item.revoked_at = now
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh session is not valid")
    # Rotate on every refresh. Reuse of an already revoked token revokes all active sessions.
    item.revoked_at = now
    raw_new = issue_refresh(db, user)
    db.commit()
    set_refresh_cookie(response, raw_new)
    return AuthOut(access_token=create_access_token(user.id), user=as_user(user))


@router.post("/logout", status_code=204, dependencies=[Depends(require_same_origin)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        item = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == digest_token(raw)))
        if item and not item.revoked_at:
            item.revoked_at = now_utc()
            db.commit()
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth", secure=get_settings().cookie_secure,
                           httponly=True, samesite="lax")


@router.post("/forgot-password", status_code=202, dependencies=[Depends(require_same_origin)])
def forgot_password(data: EmailIn, request: Request, background_tasks: BackgroundTasks,
                    db: Session = Depends(get_db)):
    enforce_rate_limit(request, "forgot", limit=5)
    generic = {"message": "If an account matches that email, password reset instructions have been sent."}
    user = db.scalar(select(User).where(User.email == data.email))
    if user and user.is_active:
        raw = opaque_token()
        db.add(PasswordReset(user_id=user.id, token_hash=digest_token(raw),
                             expires_at=now_utc() + timedelta(minutes=get_settings().reset_token_minutes)))
        db.commit()
        background_tasks.add_task(deliver_reset_email, user.email, raw)
    return generic


@router.post("/reset-password", status_code=204, dependencies=[Depends(require_same_origin)])
def reset_password(data: ResetPasswordIn, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit(request, "reset", limit=8)
    item = db.scalar(select(PasswordReset).where(PasswordReset.token_hash == digest_token(data.token)).with_for_update())
    if not item or item.used_at or expired_at(item.expires_at, now_utc()):
        raise HTTPException(status_code=400, detail="Password reset link is invalid or expired")
    user = db.get(User, item.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Password reset link is invalid or expired")
    item.used_at = now_utc()
    user.password_hash = hash_password(data.new_password)
    for other in db.scalars(select(PasswordReset).where(
            PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None))):
        other.used_at = now_utc()
    invalidate_user_refreshes(db, user.id)
    db.commit()
