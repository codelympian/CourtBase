"""Tournament endpoints, including nested events and finalize."""

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
from app.models.enums import TournamentStatus
from app.models.user import User
from app.schemas.common import Message, Page
from app.schemas.tournament import (
    EventCreate,
    EventRead,
    TournamentCreate,
    TournamentRead,
    TournamentReadDetail,
    TournamentUpdate,
)
from app.services import event_service, tournament_service
from app.services.audit_service import record_audit

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


@router.get("", response_model=Page[TournamentRead])
def list_tournaments(
    q: str | None = Query(default=None),
    status_filter: TournamentStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    items, total = tournament_service.list_tournaments(
        db, tenant_id=tenant_id, q=q, status=status_filter, page=page, size=size
    )
    return Page.create(items=items, total=total, page=page, size=size)


@router.get("/{tournament_id}", response_model=TournamentReadDetail)
def get_tournament(
    tournament_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    t = tournament_service.get_tournament(db, tournament_id, tenant_id=tenant_id)
    base = TournamentRead.model_validate(t).model_dump()
    return TournamentReadDetail(**base, **tournament_service.tournament_detail(db, t))


@router.post("", response_model=TournamentRead, status_code=status.HTTP_201_CREATED)
def create_tournament(
    request: Request,
    body: TournamentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_TOURNAMENTS)),
):
    obj = tournament_service.create_tournament(db, body, user_federation_id=user.federation_id)
    record_audit(
        db,
        action="tournament.create",
        actor_user_id=user.id,
        federation_id=obj.federation_id,
        entity_type="tournament",
        entity_id=str(obj.id),
        after={"name": obj.name},
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return obj


@router.put("/{tournament_id}", response_model=TournamentRead)
def update_tournament(
    tournament_id: uuid.UUID,
    body: TournamentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_TOURNAMENTS)),
):
    obj = tournament_service.update_tournament(
        db, tournament_id, body, tenant_id=user.federation_id
    )
    record_audit(
        db,
        action="tournament.update",
        actor_user_id=user.id,
        federation_id=obj.federation_id,
        entity_type="tournament",
        entity_id=str(obj.id),
        after=body.model_dump(exclude_unset=True, mode="json"),
    )
    return obj


@router.delete("/{tournament_id}", response_model=Message)
def delete_tournament(
    tournament_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_TOURNAMENTS)),
):
    tournament_service.delete_tournament(db, tournament_id, tenant_id=user.federation_id)
    record_audit(
        db,
        action="tournament.delete",
        actor_user_id=user.id,
        federation_id=user.federation_id,
        entity_type="tournament",
        entity_id=str(tournament_id),
    )
    return Message(detail="Tournament deleted")


@router.post("/{tournament_id}/finalize", response_model=TournamentRead)
def finalize_tournament(
    tournament_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.FINALIZE_TOURNAMENTS)),
):
    obj = tournament_service.finalize_tournament(
        db, tournament_id, tenant_id=user.federation_id
    )
    record_audit(
        db,
        action="tournament.finalize",
        actor_user_id=user.id,
        federation_id=obj.federation_id,
        entity_type="tournament",
        entity_id=str(obj.id),
    )
    return obj


# ---------------------------------------------------------------- nested events


@router.get("/{tournament_id}/events", response_model=list[EventRead])
def list_tournament_events(
    tournament_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    return event_service.list_events(db, tournament_id, tenant_id=tenant_id)


@router.post(
    "/{tournament_id}/events", response_model=EventRead, status_code=status.HTTP_201_CREATED
)
def create_tournament_event(
    request: Request,
    tournament_id: uuid.UUID,
    body: EventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_TOURNAMENTS)),
):
    obj = event_service.create_event(
        db, tournament_id, body, tenant_id=user.federation_id
    )
    record_audit(
        db,
        action="event.create",
        actor_user_id=user.id,
        federation_id=obj.federation_id,
        entity_type="event",
        entity_id=str(obj.id),
        after={"name": obj.name},
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return obj
