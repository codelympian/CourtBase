"""Business logic for tournament events."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.registration import Registration
from app.models.tournament import Event, EventCategory, Tournament
from app.schemas.tournament import EventCreate, EventUpdate
from app.services.crud import scope_to_tenant
from app.services.errors import ConflictError, NotFoundError, ValidationError
from app.services.tournament_service import get_tournament


def _get_category(
    db: Session, category_id: uuid.UUID, *, tenant_id: uuid.UUID | None
) -> EventCategory:
    from app.services.event_category_service import get_category

    return get_category(db, category_id, tenant_id=tenant_id)


def list_events(
    db: Session, tournament_id: uuid.UUID, *, tenant_id: uuid.UUID | None
) -> list[Event]:
    # Ensure the tournament itself is in scope before listing its events.
    get_tournament(db, tournament_id, tenant_id=tenant_id)
    stmt = select(Event).where(
        Event.tournament_id == tournament_id, Event.deleted_at.is_(None)
    )
    stmt = scope_to_tenant(stmt, Event, tenant_id)
    stmt = stmt.order_by(Event.name)
    return list(db.execute(stmt).scalars().all())


def get_event(db: Session, event_id: uuid.UUID, *, tenant_id: uuid.UUID | None) -> Event:
    stmt = select(Event).where(Event.id == event_id, Event.deleted_at.is_(None))
    stmt = scope_to_tenant(stmt, Event, tenant_id)
    obj = db.execute(stmt).scalar_one_or_none()
    if obj is None:
        raise NotFoundError("Event not found")
    return obj


def event_detail(db: Session, event: Event) -> dict:
    category = db.execute(
        select(EventCategory).where(EventCategory.id == event.category_id)
    ).scalar_one_or_none()
    registration_count = db.execute(
        select(func.count())
        .select_from(Registration)
        .where(Registration.event_id == event.id, Registration.deleted_at.is_(None))
    ).scalar_one()
    return {
        "category_name": category.name if category else None,
        "registration_count": registration_count,
    }


def create_event(
    db: Session,
    tournament_id: uuid.UUID,
    data: EventCreate,
    *,
    tenant_id: uuid.UUID | None,
) -> Event:
    tournament = get_tournament(db, tournament_id, tenant_id=tenant_id)
    category = _get_category(db, data.category_id, tenant_id=tournament.federation_id)
    obj = Event(
        federation_id=tournament.federation_id,
        tournament_id=tournament.id,
        category_id=category.id,
        name=data.name or category.name,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("This tournament already has an event in that category") from exc
    db.refresh(obj)
    return obj


def update_event(
    db: Session, event_id: uuid.UUID, data: EventUpdate, *, tenant_id: uuid.UUID | None
) -> Event:
    obj = get_event(db, event_id, tenant_id=tenant_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_event(db: Session, event_id: uuid.UUID, *, tenant_id: uuid.UUID | None) -> None:
    obj = get_event(db, event_id, tenant_id=tenant_id)
    if obj.draw_size:
        raise ValidationError("Cannot delete an event that already has a generated draw")
    obj.deleted_at = datetime.now(UTC)
    db.commit()


def get_tournament_for_event(
    db: Session, event: Event, *, tenant_id: uuid.UUID | None
) -> Tournament:
    return get_tournament(db, event.tournament_id, tenant_id=tenant_id)
