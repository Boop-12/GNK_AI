from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user, require_authority
from app.models import User
from app.schemas import UserOut

router = APIRouter(tags=["users"])


def user_response(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email,
                   roles=[role.name for role in user.roles],
                   authorities=sorted({p.name for role in user.roles for p in role.authorities}))


@router.get("/users/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user_response(user)


@router.get("/admin/users", dependencies=[Depends(require_authority("users:read"))])
def list_users(db: Session = Depends(get_db)):
    return [user_response(user) for user in db.query(User).order_by(User.id).all()]
