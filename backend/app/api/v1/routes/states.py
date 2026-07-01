"""State association endpoints."""

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
from app.schemas.common import Message, Page
from app.schemas.state import StateCreate, StateRead, StateUpdate
from app.services import state_service
from app.services.audit_service import record_audit

router = APIRouter(prefix="/states", tags=["states"])


@router.get("", response_model=Page[StateRead])
def list_states(
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    items, total = state_service.list_states(db, tenant_id=tenant_id, q=q, page=page, size=size)
    return Page.create(items=items, total=total, page=page, size=size)


@router.get("/{state_id}", response_model=StateRead)
def get_state(
    state_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    return state_service.get_state(db, state_id, tenant_id=tenant_id)


@router.post("", response_model=StateRead, status_code=status.HTTP_201_CREATED)
def create_state(
    request: Request,
    body: StateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_STATES)),
):
    obj = state_service.create_state(db, body, user_federation_id=user.federation_id)
    record_audit(
        db,
        action="state.create",
        actor_user_id=user.id,
        federation_id=obj.federation_id,
        entity_type="state_association",
        entity_id=str(obj.id),
        after={"name": obj.name},
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return obj


@router.put("/{state_id}", response_model=StateRead)
def update_state(
    request: Request,
    state_id: uuid.UUID,
    body: StateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_STATES)),
):
    obj = state_service.update_state(db, state_id, body, tenant_id=user.federation_id)
    record_audit(
        db,
        action="state.update",
        actor_user_id=user.id,
        federation_id=obj.federation_id,
        entity_type="state_association",
        entity_id=str(obj.id),
        after=body.model_dump(exclude_unset=True, mode="json"),
    )
    return obj


@router.delete("/{state_id}", response_model=Message)
def delete_state(
    state_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_STATES)),
):
    state_service.delete_state(db, state_id, tenant_id=user.federation_id)
    record_audit(
        db,
        action="state.delete",
        actor_user_id=user.id,
        federation_id=user.federation_id,
        entity_type="state_association",
        entity_id=str(state_id),
    )
    return Message(detail="State association deleted")
