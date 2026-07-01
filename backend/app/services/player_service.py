"""Business logic for players."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import Gender, PlayerStatus
from app.models.org import Club, StateAssociation
from app.models.player import Player
from app.schemas.player import PlayerCreate, PlayerUpdate
from app.services.crud import paginate, resolve_write_federation, scope_to_tenant
from app.services.errors import ConflictError, NotFoundError, ValidationError
from app.utils.age import age_category, calculate_age


def validate_club(db: Session, club_id: uuid.UUID | None, federation_id: uuid.UUID) -> None:
    if club_id is None:
        return
    ok = db.execute(
        select(Club.id).where(
            Club.id == club_id,
            Club.federation_id == federation_id,
            Club.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if ok is None:
        raise ValidationError("club_id does not reference a club in this federation")


def validate_state(db: Session, state_id: uuid.UUID | None, federation_id: uuid.UUID) -> None:
    if state_id is None:
        return
    ok = db.execute(
        select(StateAssociation.id).where(
            StateAssociation.id == state_id,
            StateAssociation.federation_id == federation_id,
            StateAssociation.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if ok is None:
        raise ValidationError("state_id does not reference a state in this federation")


def enrich(player: Player) -> dict:
    """Derived read-only fields."""
    return {
        "age": calculate_age(player.date_of_birth),
        "age_category": age_category(player.date_of_birth),
    }


def list_players(
    db: Session,
    *,
    tenant_id: uuid.UUID | None,
    q: str | None = None,
    status: PlayerStatus | None = None,
    gender: Gender | None = None,
    club_id: uuid.UUID | None = None,
    state_id: uuid.UUID | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Player], int]:
    stmt = select(Player).where(Player.deleted_at.is_(None))
    stmt = scope_to_tenant(stmt, Player, tenant_id)
    if status:
        stmt = stmt.where(Player.status == status)
    if gender:
        stmt = stmt.where(Player.gender == gender)
    if club_id:
        stmt = stmt.where(Player.club_id == club_id)
    if state_id:
        stmt = stmt.where(Player.state_id == state_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Player.full_name.ilike(like),
                Player.federation_player_code.ilike(like),
                Player.email.ilike(like),
            )
        )
    stmt = stmt.order_by(Player.full_name)
    return paginate(db, stmt, page, size)


def list_all_players(
    db: Session,
    *,
    tenant_id: uuid.UUID | None,
    status: PlayerStatus | None = None,
    gender: Gender | None = None,
    club_id: uuid.UUID | None = None,
    state_id: uuid.UUID | None = None,
) -> list[Player]:
    """Full, uncapped result set — used for exports."""
    stmt = select(Player).where(Player.deleted_at.is_(None))
    stmt = scope_to_tenant(stmt, Player, tenant_id)
    if status:
        stmt = stmt.where(Player.status == status)
    if gender:
        stmt = stmt.where(Player.gender == gender)
    if club_id:
        stmt = stmt.where(Player.club_id == club_id)
    if state_id:
        stmt = stmt.where(Player.state_id == state_id)
    stmt = stmt.order_by(Player.full_name)
    return list(db.execute(stmt).scalars().all())


def get_player(db: Session, player_id: uuid.UUID, *, tenant_id: uuid.UUID | None) -> Player:
    stmt = select(Player).where(Player.id == player_id, Player.deleted_at.is_(None))
    stmt = scope_to_tenant(stmt, Player, tenant_id)
    obj = db.execute(stmt).scalar_one_or_none()
    if obj is None:
        raise NotFoundError("Player not found")
    return obj


def player_detail(db: Session, player: Player) -> dict:
    club_name = None
    state_name = None
    if player.club_id:
        club_name = db.execute(
            select(Club.name).where(Club.id == player.club_id)
        ).scalar_one_or_none()
    if player.state_id:
        state_name = db.execute(
            select(StateAssociation.name).where(StateAssociation.id == player.state_id)
        ).scalar_one_or_none()
    return {**enrich(player), "club_name": club_name, "state_name": state_name}


def create_player(
    db: Session, data: PlayerCreate, *, user_federation_id: uuid.UUID | None
) -> Player:
    federation_id = resolve_write_federation(user_federation_id, data.federation_id)
    validate_club(db, data.club_id, federation_id)
    validate_state(db, data.state_id, federation_id)
    obj = Player(
        federation_id=federation_id,
        federation_player_code=data.federation_player_code,
        full_name=data.full_name,
        gender=data.gender,
        date_of_birth=data.date_of_birth,
        nationality=data.nationality,
        photo_url=data.photo_url,
        phone=data.phone,
        email=data.email,
        status=data.status,
        club_id=data.club_id,
        state_id=data.state_id,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "A player with this federation code already exists"
        ) from exc
    db.refresh(obj)
    return obj


def update_player(
    db: Session, player_id: uuid.UUID, data: PlayerUpdate, *, tenant_id: uuid.UUID | None
) -> Player:
    obj = get_player(db, player_id, tenant_id=tenant_id)
    payload = data.model_dump(exclude_unset=True)
    if "club_id" in payload:
        validate_club(db, payload["club_id"], obj.federation_id)
    if "state_id" in payload:
        validate_state(db, payload["state_id"], obj.federation_id)
    for field, value in payload.items():
        setattr(obj, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "A player with this federation code already exists"
        ) from exc
    db.refresh(obj)
    return obj


def delete_player(db: Session, player_id: uuid.UUID, *, tenant_id: uuid.UUID | None) -> None:
    obj = get_player(db, player_id, tenant_id=tenant_id)
    obj.deleted_at = datetime.now(UTC)
    db.commit()
