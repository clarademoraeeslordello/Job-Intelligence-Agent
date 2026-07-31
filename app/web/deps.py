from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.database import get_session
from app.database.models import User
from app.web.security import SESSION_COOKIE_NAME, read_session_token

DbSession = Depends(get_session)


def get_current_user(request: Request, session: Session = DbSession) -> User | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    user_id = read_session_token(token)
    if user_id is None:
        return None

    user = session.get(User, user_id)
    if user is None or not user.is_active or user.password_hash is None:
        return None
    return user


def require_login(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


def require_admin(user: User = Depends(require_login)) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores"
        )
    return user
