"""Business logic for clubs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.org import Club, StateAssociation
from app.models.player import Player
from app.schemas.club import ClubCreate, ClubUpdate
from app.services.crud import paginate, resolve_write_federation, scope_to_tenant
from app.services.errors import ConflictError, NotFoundError, ValidationError


def _validate_state(
    db: Session, state_id: uuid.UUID | None, federation_id: uuid.UUID
) -> None:
    if state_id is None:
        return
    exists = db.execute(
        select(StateAssociation.id).where(
            StateAssociation.id == state_id,
            StateAssociation.federation_id == federation_id,
            StateAssociation.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if exists is None:
        raise ValidationError("state_id does not reference a state in this federation")


def list_clubs(
    db: Session,
    *,
    tenant_id: uuid.UUID | None,
    q: str | None = None,
    state_id: uuid.UUID | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Club], int]:
    stmt = select(Club).where(Club.deleted_at.is_(None))
    stmt = scope_to_tenant(stmt, Club, tenant_id)
    if state_id:
        stmt = stmt.where(Club.state_id == state_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Club.name.ilike(like), Club.coach_name.ilike(like)))
    stmt = stmt.order_by(Club.name)
    return paginate(db, stmt, page, size)


def get_club(db: Session, club_id: uuid.UUID, *, tenant_id: uuid.UUID | None) -> Club:
    stmt = select(Club).where(Club.id == club_id, Club.deleted_at.is_(None))
    stmt = scope_to_tenant(stmt, Club, tenant_id)
    obj = db.execute(stmt).scalar_one_or_none()
    if obj is None:
        raise NotFoundError("Club not found")
    return obj


def club_detail(db: Session, club: Club) -> dict:
    """Extra read fields: state name and live player count."""
    state_name = None
    if club.state_id:
        state_name = db.execute(
            select(StateAssociation.name).where(StateAssociation.id == club.state_id)
        ).scalar_one_or_none()
    player_count = db.execute(
        select(func.count())
        .select_from(Player)
        .where(Player.club_id == club.id, Player.deleted_at.is_(None))
    ).scalar_one()
    return {"state_name": state_name, "player_count": player_count}


def create_club(
    db: Session, data: ClubCreate, *, user_federation_id: uuid.UUID | None
) -> Club:
    federation_id = resolve_write_federation(user_federation_id, data.federation_id)
    _validate_state(db, data.state_id, federation_id)
    obj = Club(
        federation_id=federation_id,
        name=data.name,
        state_id=data.state_id,
        coach_name=data.coach_name,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        address=data.address,
        logo_url=data.logo_url,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("A club with this name already exists") from exc
    db.refresh(obj)
    return obj


def update_club(
    db: Session, club_id: uuid.UUID, data: ClubUpdate, *, tenant_id: uuid.UUID | None
) -> Club:
    obj = get_club(db, club_id, tenant_id=tenant_id)
    payload = data.model_dump(exclude_unset=True)
    if "state_id" in payload:
        _validate_state(db, payload["state_id"], obj.federation_id)
    for field, value in payload.items():
        setattr(obj, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("A club with this name already exists") from exc
    db.refresh(obj)
    return obj


def delete_club(db: Session, club_id: uuid.UUID, *, tenant_id: uuid.UUID | None) -> None:
    obj = get_club(db, club_id, tenant_id=tenant_id)
    obj.deleted_at = datetime.now(UTC)
    db.commit()
