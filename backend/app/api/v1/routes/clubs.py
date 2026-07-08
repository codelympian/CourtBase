"""Club endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import (
    get_current_active_user,
    get_tenant_id,
    require_permission,
)
from app.core.rbac import Permission
from app.models.user import User
from app.schemas.club import ClubCreate, ClubRead, ClubReadDetail, ClubUpdate
from app.schemas.common import Message, Page
from app.services import club_service, storage_service
from app.services.audit_service import record_audit

router = APIRouter(prefix="/clubs", tags=["clubs"])


@router.get("", response_model=Page[ClubRead])
def list_clubs(
    q: str | None = Query(default=None),
    state_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    items, total = club_service.list_clubs(
        db, tenant_id=tenant_id, q=q, state_id=state_id, page=page, size=size
    )
    return Page.create(items=items, total=total, page=page, size=size)


@router.get("/{club_id}", response_model=ClubReadDetail)
def get_club(
    club_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    club = club_service.get_club(db, club_id, tenant_id=tenant_id)
    base = ClubRead.model_validate(club).model_dump()
    return ClubReadDetail(**base, **club_service.club_detail(db, club))


@router.post("", response_model=ClubRead, status_code=status.HTTP_201_CREATED)
def create_club(
    request: Request,
    body: ClubCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_CLUBS)),
):
    obj = club_service.create_club(db, body, user_federation_id=user.federation_id)
    record_audit(
        db,
        action="club.create",
        actor_user_id=user.id,
        federation_id=obj.federation_id,
        entity_type="club",
        entity_id=str(obj.id),
        after={"name": obj.name},
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return obj


@router.put("/{club_id}", response_model=ClubRead)
def update_club(
    club_id: uuid.UUID,
    body: ClubUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_CLUBS)),
):
    obj = club_service.update_club(db, club_id, body, tenant_id=user.federation_id)
    record_audit(
        db,
        action="club.update",
        actor_user_id=user.id,
        federation_id=obj.federation_id,
        entity_type="club",
        entity_id=str(obj.id),
        after=body.model_dump(exclude_unset=True, mode="json"),
    )
    return obj


@router.delete("/{club_id}", response_model=Message)
def delete_club(
    club_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_CLUBS)),
):
    club_service.delete_club(db, club_id, tenant_id=user.federation_id)
    record_audit(
        db,
        action="club.delete",
        actor_user_id=user.id,
        federation_id=user.federation_id,
        entity_type="club",
        entity_id=str(club_id),
    )
    return Message(detail="Club deleted")


@router.post("/{club_id}/logo", response_model=ClubRead)
def upload_club_logo(
    club_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_CLUBS)),
):
    bucket = settings.STORAGE_CLUB_LOGOS_BUCKET
    club = club_service.get_club(db, club_id, tenant_id=user.federation_id)
    content, ext = storage_service.read_and_validate(file)
    path = f"{club.federation_id}/{club.id}.{ext}"
    url = storage_service.upload_image(bucket, path, content, ext)
    club, previous = club_service.set_logo_url(
        db, club_id, url=url, tenant_id=user.federation_id
    )
    prev_path = storage_service.object_path_from_url(bucket, previous)
    if prev_path and prev_path != path:
        storage_service.delete_object(bucket, prev_path)
    record_audit(
        db,
        action="club.logo.upload",
        actor_user_id=user.id,
        federation_id=club.federation_id,
        entity_type="club",
        entity_id=str(club.id),
    )
    return club


@router.delete("/{club_id}/logo", response_model=ClubRead)
def delete_club_logo(
    club_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_CLUBS)),
):
    bucket = settings.STORAGE_CLUB_LOGOS_BUCKET
    club, previous = club_service.set_logo_url(
        db, club_id, url=None, tenant_id=user.federation_id
    )
    prev_path = storage_service.object_path_from_url(bucket, previous)
    if prev_path:
        storage_service.delete_object(bucket, prev_path)
    record_audit(
        db,
        action="club.logo.delete",
        actor_user_id=user.id,
        federation_id=club.federation_id,
        entity_type="club",
        entity_id=str(club.id),
    )
    return club
