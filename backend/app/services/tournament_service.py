"""Business logic for tournaments."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import MatchStatus, TournamentStatus
from app.models.match import Match
from app.models.tournament import Event, Tournament
from app.schemas.tournament import TournamentCreate, TournamentUpdate
from app.services.crud import paginate, resolve_write_federation, scope_to_tenant
from app.services.errors import NotFoundError, ValidationError

# Matches in these states still require attention before a tournament can be finalized.
_INCOMPLETE_MATCH_STATUSES = (MatchStatus.scheduled, MatchStatus.in_progress)


def list_tournaments(
    db: Session,
    *,
    tenant_id: uuid.UUID | None,
    q: str | None = None,
    status: TournamentStatus | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Tournament], int]:
    stmt = select(Tournament).where(Tournament.deleted_at.is_(None))
    stmt = scope_to_tenant(stmt, Tournament, tenant_id)
    if status:
        stmt = stmt.where(Tournament.status == status)
    if q:
        stmt = stmt.where(or_(Tournament.name.ilike(f"%{q.strip()}%")))
    stmt = stmt.order_by(Tournament.start_date.desc().nulls_last(), Tournament.name)
    return paginate(db, stmt, page, size)


def get_tournament(
    db: Session, tournament_id: uuid.UUID, *, tenant_id: uuid.UUID | None
) -> Tournament:
    stmt = select(Tournament).where(
        Tournament.id == tournament_id, Tournament.deleted_at.is_(None)
    )
    stmt = scope_to_tenant(stmt, Tournament, tenant_id)
    obj = db.execute(stmt).scalar_one_or_none()
    if obj is None:
        raise NotFoundError("Tournament not found")
    return obj


def tournament_detail(db: Session, tournament: Tournament) -> dict:
    event_count = db.execute(
        select(func.count())
        .select_from(Event)
        .where(Event.tournament_id == tournament.id, Event.deleted_at.is_(None))
    ).scalar_one()
    return {"event_count": event_count}


def create_tournament(
    db: Session, data: TournamentCreate, *, user_federation_id: uuid.UUID | None
) -> Tournament:
    federation_id = resolve_write_federation(user_federation_id, data.federation_id)
    obj = Tournament(
        federation_id=federation_id,
        name=data.name,
        venue=data.venue,
        start_date=data.start_date,
        end_date=data.end_date,
        level=data.level,
        organizer=data.organizer,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_tournament(
    db: Session,
    tournament_id: uuid.UUID,
    data: TournamentUpdate,
    *,
    tenant_id: uuid.UUID | None,
) -> Tournament:
    obj = get_tournament(db, tournament_id, tenant_id=tenant_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_tournament(
    db: Session, tournament_id: uuid.UUID, *, tenant_id: uuid.UUID | None
) -> None:
    obj = get_tournament(db, tournament_id, tenant_id=tenant_id)
    obj.deleted_at = datetime.now(UTC)
    db.commit()


def finalize_tournament(
    db: Session, tournament_id: uuid.UUID, *, tenant_id: uuid.UUID | None
) -> Tournament:
    """Transition a tournament to ``completed``.

    Refuses if any of its matches are still scheduled or in progress, so
    officials can't accidentally close a tournament with unfinished business.
    Ranking points are awarded separately by the ranking engine (Phase 4).
    """
    obj = get_tournament(db, tournament_id, tenant_id=tenant_id)
    incomplete = db.execute(
        select(func.count())
        .select_from(Match)
        .join(Event, Event.id == Match.event_id)
        .where(
            Event.tournament_id == tournament_id,
            Match.deleted_at.is_(None),
            Match.status.in_(_INCOMPLETE_MATCH_STATUSES),
        )
    ).scalar_one()
    if incomplete:
        raise ValidationError(
            f"Cannot finalize: {incomplete} match(es) are still scheduled or in progress"
        )
    obj.status = TournamentStatus.completed
    db.commit()
    db.refresh(obj)
    return obj
