import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                     db: Session = Depends(get_db)) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    try:
        user_id = decode_access_token(credentials.credentials)
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"}) from None
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"})
    return user


def require_authority(authority: str):
    def check(user: User = Depends(get_current_user)) -> User:
        granted = {permission.name for role in user.roles for permission in role.authorities}
        if authority not in granted:
            raise HTTPException(status_code=403, detail="Insufficient permission")
        return user
    return check


def require_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin or origin.rstrip("/") != request.app.state.frontend_origin.rstrip("/"):
        raise HTTPException(status_code=403, detail="Request origin is not allowed")
