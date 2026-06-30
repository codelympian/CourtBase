"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserPublic,
)
from app.schemas.common import Message
from app.services import auth_service
from app.services.audit_service import record_audit

router = APIRouter(prefix="/auth", tags=["auth"])


def _client(request: Request) -> tuple[str | None, str | None]:
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    return ua, ip


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = auth_service.register_user(
            db,
            email=body.email,
            password=body.password,
            full_name=body.full_name,
            federation_id=body.federation_id,
        )
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    ua, ip = _client(request)
    record_audit(
        db,
        action="auth.register",
        actor_user_id=user.id,
        federation_id=user.federation_id,
        entity_type="user",
        entity_id=str(user.id),
        ip=ip,
        user_agent=ua,
    )
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = auth_service.authenticate(db, email=body.email, password=body.password)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    ua, ip = _client(request)
    tokens = auth_service.issue_tokens(db, user=user, user_agent=ua, ip=ip)
    record_audit(
        db,
        action="auth.login",
        actor_user_id=user.id,
        federation_id=user.federation_id,
        ip=ip,
        user_agent=ua,
    )
    return tokens


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def refresh(request: Request, body: RefreshRequest, db: Session = Depends(get_db)):
    ua, ip = _client(request)
    try:
        return auth_service.rotate_refresh_token(
            db, refresh_token=body.refresh_token, user_agent=ua, ip=ip
        )
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/logout", response_model=Message)
def logout(body: LogoutRequest, db: Session = Depends(get_db)):
    auth_service.revoke_refresh_token(db, refresh_token=body.refresh_token)
    return Message(detail="Logged out")


@router.post("/password/forgot", response_model=Message)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def forgot_password(
    request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)
):
    token = auth_service.create_password_reset(db, email=body.email)
    # In production the token is emailed; never returned in the response.
    if token and not settings.is_production:
        return Message(detail=f"Reset token (dev only): {token}")
    return Message(detail="If that email exists, a reset link has been sent")


@router.post("/password/reset", response_model=Message)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def reset_password(
    request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)
):
    try:
        auth_service.reset_password(db, token=body.token, new_password=body.new_password)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Message(detail="Password updated")


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_active_user)):
    return auth_service.me_payload(current_user)
