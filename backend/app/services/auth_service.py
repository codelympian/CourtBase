"""Authentication business logic: registration, login, token rotation, reset."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rbac import permissions_for_roles
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_reset_token,
    decode_token,
    hash_password,
    hash_token,
    needs_rehash,
    verify_password,
)
from app.models.role import Role
from app.models.user import RefreshToken, User


class AuthError(Exception):
    """Raised on authentication/authorization failures in the service layer."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


def get_user_by_email(
    db: Session, email: str, federation_id: uuid.UUID | None
) -> User | None:
    stmt = select(User).where(
        User.email == email.lower(), User.deleted_at.is_(None)
    )
    # Scope by federation when provided; platform admins have NULL federation.
    if federation_id is not None:
        stmt = stmt.where(User.federation_id == federation_id)
    return db.execute(stmt).scalar_one_or_none()


def register_user(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    federation_id: uuid.UUID | None = None,
    role_names: list[str] | None = None,
) -> User:
    existing = db.execute(
        select(User).where(
            User.email == email.lower(),
            User.federation_id == federation_id,
            User.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if existing:
        raise AuthError("A user with this email already exists")

    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        full_name=full_name,
        federation_id=federation_id,
        is_active=True,
    )
    if role_names:
        roles = db.execute(select(Role).where(Role.name.in_(role_names))).scalars().all()
        user.roles = list(roles)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(
    db: Session, *, email: str, password: str, federation_id: uuid.UUID | None = None
) -> User:
    user = get_user_by_email(db, email, federation_id)
    if user is None:
        # Run a dummy verify to reduce user-enumeration timing differences.
        verify_password(password, hash_password("dummy"))
        raise AuthError("Invalid email or password")
    if not verify_password(password, user.hashed_password):
        raise AuthError("Invalid email or password")
    if not user.is_active:
        raise AuthError("Account is disabled")

    if needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(password)

    user.last_login_at = _utcnow()
    db.commit()
    return user


def _store_refresh_token(
    db: Session,
    *,
    user: User,
    token: str,
    family_id: uuid.UUID,
    user_agent: str | None,
    ip: str | None,
) -> None:
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(token),
            family_id=family_id,
            expires_at=_utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            user_agent=user_agent,
            ip=ip,
            created_at=_utcnow(),
        )
    )


def issue_tokens(
    db: Session, *, user: User, user_agent: str | None = None, ip: str | None = None
) -> dict:
    family_id = uuid.uuid4()
    access = create_access_token(str(user.id), extra={"roles": user.role_names})
    refresh = create_refresh_token(str(user.id), family_id=str(family_id))
    _store_refresh_token(
        db, user=user, token=refresh, family_id=family_id, user_agent=user_agent, ip=ip
    )
    db.commit()
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def rotate_refresh_token(
    db: Session, *, refresh_token: str, user_agent: str | None = None, ip: str | None = None
) -> dict:
    try:
        decode_token(refresh_token, expected_type="refresh")
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid refresh token") from exc

    token_hash = hash_token(refresh_token)
    record = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()

    if record is None:
        raise AuthError("Invalid refresh token")

    if record.revoked_at is not None:
        # Reuse of an already-rotated token → revoke the whole family.
        for tok in db.execute(
            select(RefreshToken).where(
                RefreshToken.family_id == record.family_id,
                RefreshToken.revoked_at.is_(None),
            )
        ).scalars():
            tok.revoked_at = _utcnow()
        db.commit()
        raise AuthError("Refresh token reuse detected; session revoked")

    if not record.is_active:
        raise AuthError("Refresh token expired")

    user = db.get(User, record.user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise AuthError("User no longer active")

    # Rotate: revoke old, issue new within the same family.
    record.revoked_at = _utcnow()
    access = create_access_token(str(user.id), extra={"roles": user.role_names})
    new_refresh = create_refresh_token(str(user.id), family_id=str(record.family_id))
    _store_refresh_token(
        db,
        user=user,
        token=new_refresh,
        family_id=record.family_id,
        user_agent=user_agent,
        ip=ip,
    )
    db.commit()
    return {
        "access_token": access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def revoke_refresh_token(db: Session, *, refresh_token: str) -> None:
    record = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    ).scalar_one_or_none()
    if record and record.revoked_at is None:
        record.revoked_at = _utcnow()
        db.commit()


def create_password_reset(db: Session, *, email: str) -> str | None:
    """Return a reset token if the user exists (caller should not leak existence)."""
    user = db.execute(
        select(User).where(User.email == email.lower(), User.deleted_at.is_(None))
    ).scalar_one_or_none()
    if user is None:
        return None
    return create_reset_token(str(user.id))


def reset_password(db: Session, *, token: str, new_password: str) -> None:
    try:
        payload = decode_token(token, expected_type="reset")
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid or expired reset token") from exc

    user = db.get(User, uuid.UUID(str(payload.get("sub"))))
    if user is None or user.deleted_at is not None:
        raise AuthError("Invalid reset token")

    user.hashed_password = hash_password(new_password)
    # Revoke all active refresh tokens on password change.
    for tok in db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
        )
    ).scalars():
        tok.revoked_at = _utcnow()
    db.commit()


def me_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "federation_id": user.federation_id,
        "roles": user.role_names,
        "permissions": sorted(permissions_for_roles(user.role_names)),
    }
