"""Reusable FastAPI dependencies: auth, RBAC guards, tenant scoping."""

from __future__ import annotations

import uuid
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import has_permission
from app.core.security import decode_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise _CREDENTIALS_EXC
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id = payload.get("sub")
        if user_id is None:
            raise _CREDENTIALS_EXC
    except jwt.PyJWTError:
        raise _CREDENTIALS_EXC from None

    user = db.execute(
        select(User).where(User.id == uuid.UUID(str(user_id)), User.deleted_at.is_(None))
    ).scalar_one_or_none()
    if user is None:
        raise _CREDENTIALS_EXC
    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


def require_roles(*roles: str) -> Callable[..., User]:
    """Dependency factory: allow only users having at least one of ``roles``."""

    def _guard(user: User = Depends(get_current_active_user)) -> User:
        if user.is_superuser:
            return user
        if not set(roles) & set(user.role_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return user

    return _guard


def require_permission(permission: str) -> Callable[..., User]:
    """Dependency factory: allow only users whose roles grant ``permission``."""

    def _guard(user: User = Depends(get_current_active_user)) -> User:
        if user.is_superuser:
            return user
        if not has_permission(user.role_names, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permission",
            )
        return user

    return _guard


def get_tenant_id(user: User = Depends(get_current_active_user)) -> uuid.UUID | None:
    """Resolve the caller's federation scope. ``None`` for platform super admins."""
    return user.federation_id
