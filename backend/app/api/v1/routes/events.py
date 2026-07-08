"""Event endpoints: detail, registrations, draw generation, and bracket view."""

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
from app.schemas.match import BracketMatch, MatchRead
from app.schemas.registration import RegistrationCreate, RegistrationRead
from app.schemas.tournament import EventRead, EventReadDetail, EventUpdate
from app.services import draw_service, event_service, match_service, registration_service
from app.services.audit_service import record_audit

router = APIRouter(prefix="/events", tags=["events"])


def _detail(db: Session, event) -> EventReadDetail:
    base = EventRead.model_validate(event).model_dump()
    return EventReadDetail(**base, **event_service.event_detail(db, event))


@router.get("/{event_id}", response_model=EventReadDetail)
def get_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    event = event_service.get_event(db, event_id, tenant_id=tenant_id)
    return _detail(db, event)


@router.put("/{event_id}", response_model=EventReadDetail)
def update_event(
    event_id: uuid.UUID,
    body: EventUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_TOURNAMENTS)),
):
    event = event_service.update_event(db, event_id, body, tenant_id=user.federation_id)
    record_audit(
        db,
        action="event.update",
        actor_user_id=user.id,
        federation_id=event.federation_id,
        entity_type="event",
        entity_id=str(event.id),
        after=body.model_dump(exclude_unset=True, mode="json"),
    )
    return _detail(db, event)


@router.delete("/{event_id}", response_model=Message)
def delete_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_TOURNAMENTS)),
):
    event_service.delete_event(db, event_id, tenant_id=user.federation_id)
    record_audit(
        db,
        action="event.delete",
        actor_user_id=user.id,
        federation_id=user.federation_id,
        entity_type="event",
        entity_id=str(event_id),
    )
    return Message(detail="Event deleted")


# ---------------------------------------------------------------- registrations


@router.get("/{event_id}/registrations", response_model=Page[RegistrationRead])
def list_registrations(
    event_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    items, total = registration_service.list_registrations(
        db, event_id, tenant_id=tenant_id, page=page, size=size
    )
    return Page.create(items=items, total=total, page=page, size=size)


@router.post(
    "/{event_id}/registrations",
    response_model=RegistrationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_registration(
    request: Request,
    event_id: uuid.UUID,
    body: RegistrationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_TOURNAMENTS)),
):
    obj = registration_service.create_registration(
        db, event_id, body, tenant_id=user.federation_id
    )
    record_audit(
        db,
        action="registration.create",
        actor_user_id=user.id,
        federation_id=obj.federation_id,
        entity_type="registration",
        entity_id=str(obj.id),
        after={"player_id": str(obj.player_id)},
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return obj


# ----------------------------------------------------------------- draw / bracket


@router.post("/{event_id}/draw", response_model=list[BracketMatch])
def generate_draw(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_DRAWS)),
):
    event = event_service.get_event(db, event_id, tenant_id=user.federation_id)
    matches = draw_service.generate_draw(db, event)
    record_audit(
        db,
        action="event.draw_generated",
        actor_user_id=user.id,
        federation_id=event.federation_id,
        entity_type="event",
        entity_id=str(event.id),
        after={"draw_size": event.draw_size},
    )
    return _bracket_response(db, matches)


@router.get("/{event_id}/draw", response_model=list[BracketMatch])
def get_draw(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    matches = match_service.list_bracket(db, event_id, tenant_id=tenant_id)
    return _bracket_response(db, matches)


@router.delete("/{event_id}/draw", response_model=Message)
def reset_draw(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_DRAWS)),
):
    event = event_service.get_event(db, event_id, tenant_id=user.federation_id)
    draw_service.reset_draw(db, event)
    record_audit(
        db,
        action="event.draw_reset",
        actor_user_id=user.id,
        federation_id=event.federation_id,
        entity_type="event",
        entity_id=str(event.id),
    )
    return Message(detail="Draw reset")


def _bracket_response(db: Session, matches: list) -> list[BracketMatch]:
    counts_by_round: dict[int, int] = {}
    for m in matches:
        counts_by_round[m.round] = counts_by_round.get(m.round, 0) + 1
    out = []
    for m in matches:
        base = MatchRead.model_validate(m).model_dump()
        out.append(
            BracketMatch(
                **base,
                **match_service.match_detail(db, m),
                round_name=draw_service.round_name(counts_by_round[m.round]),
            )
        )
    return out
