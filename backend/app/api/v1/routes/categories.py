"""Event category endpoints (Senior/Junior disciplines, plus custom additions)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_active_user,
    get_tenant_id,
    require_permission,
)
from app.core.rbac import Permission
from app.models.user import User
from app.schemas.common import Message
from app.schemas.tournament import EventCategoryCreate, EventCategoryRead, EventCategoryUpdate
from app.services import event_category_service
from app.services.audit_service import record_audit

router = APIRouter(prefix="/event-categories", tags=["event-categories"])


@router.get("", response_model=list[EventCategoryRead])
def list_categories(
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    return event_category_service.list_categories(db, tenant_id=tenant_id, active_only=active_only)


@router.get("/{category_id}", response_model=EventCategoryRead)
def get_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    return event_category_service.get_category(db, category_id, tenant_id=tenant_id)


@router.post("", response_model=EventCategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    request: Request,
    body: EventCategoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_TOURNAMENTS)),
):
    obj = event_category_service.create_category(db, body, user=user)
    record_audit(
        db,
        action="event_category.create",
        actor_user_id=user.id,
        federation_id=obj.federation_id,
        entity_type="event_category",
        entity_id=str(obj.id),
        after={"code": obj.code, "name": obj.name},
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return obj


@router.put("/{category_id}", response_model=EventCategoryRead)
def update_category(
    category_id: uuid.UUID,
    body: EventCategoryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_TOURNAMENTS)),
):
    obj = event_category_service.update_category(db, category_id, body, user=user)
    record_audit(
        db,
        action="event_category.update",
        actor_user_id=user.id,
        federation_id=obj.federation_id,
        entity_type="event_category",
        entity_id=str(obj.id),
        after=body.model_dump(exclude_unset=True, mode="json"),
    )
    return obj


@router.delete("/{category_id}", response_model=Message)
def delete_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_TOURNAMENTS)),
):
    event_category_service.delete_category(db, category_id, user=user)
    record_audit(
        db,
        action="event_category.delete",
        actor_user_id=user.id,
        entity_type="event_category",
        entity_id=str(category_id),
    )
    return Message(detail="Event category deleted")
