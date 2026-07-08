"""Business logic for event registrations.

Validates age eligibility, active membership, duplicate registration, category
gender scope, and (for mixed doubles) that partners are of different genders —
per the spec's "System validates: Age eligibility, Membership, Duplicate
registration."
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import (
    Discipline,
    GenderScope,
    PlayerStatus,
    RegistrationStatus,
    TournamentStatus,
)
from app.models.player import Player
from app.models.registration import Registration
from app.models.tournament import EventCategory
from app.schemas.registration import RegistrationCreate, RegistrationUpdate
from app.services.crud import paginate, scope_to_tenant
from app.services.errors import ConflictError, NotFoundError, ValidationError
from app.services.event_service import get_event, get_tournament_for_event
from app.utils.age import calculate_age


def _get_active_player(db: Session, player_id: uuid.UUID, federation_id: uuid.UUID) -> Player:
    player = db.execute(
        select(Player).where(
            Player.id == player_id,
            Player.federation_id == federation_id,
            Player.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if player is None:
        raise ValidationError("Player does not belong to this federation")
    if player.status != PlayerStatus.active:
        raise ValidationError(f"Player {player.full_name} is not an active member")
    return player


def _check_age_eligibility(player: Player, category: EventCategory) -> None:
    if category.age_min is None and category.age_max is None:
        return
    age = calculate_age(player.date_of_birth)
    if age is None:
        raise ValidationError(
            f"Player {player.full_name} has no date of birth on file, "
            f"required for age-restricted category '{category.name}'"
        )
    if category.age_min is not None and age < category.age_min:
        raise ValidationError(
            f"Player {player.full_name} (age {age}) is below the minimum age "
            f"({category.age_min}) for '{category.name}'"
        )
    if category.age_max is not None and age > category.age_max:
        raise ValidationError(
            f"Player {player.full_name} (age {age}) exceeds the maximum age "
            f"({category.age_max}) for '{category.name}'"
        )


def _check_gender_scope(player: Player, partner: Player | None, category: EventCategory) -> None:
    if category.gender_scope == GenderScope.men and player.gender.value != "M":
        raise ValidationError(f"'{category.name}' is restricted to male players")
    if category.gender_scope == GenderScope.women and player.gender.value != "F":
        raise ValidationError(f"'{category.name}' is restricted to female players")
    if category.gender_scope == GenderScope.mixed and partner is not None:
        if player.gender == partner.gender:
            raise ValidationError("Mixed doubles requires one male and one female player")


def list_registrations(
    db: Session,
    event_id: uuid.UUID,
    *,
    tenant_id: uuid.UUID | None,
    page: int = 1,
    size: int = 50,
) -> tuple[list[Registration], int]:
    get_event(db, event_id, tenant_id=tenant_id)
    stmt = select(Registration).where(
        Registration.event_id == event_id, Registration.deleted_at.is_(None)
    )
    stmt = scope_to_tenant(stmt, Registration, tenant_id)
    stmt = stmt.order_by(Registration.seed.is_(None), Registration.seed, Registration.created_at)
    return paginate(db, stmt, page, size)


def get_registration(
    db: Session, registration_id: uuid.UUID, *, tenant_id: uuid.UUID | None
) -> Registration:
    stmt = select(Registration).where(
        Registration.id == registration_id, Registration.deleted_at.is_(None)
    )
    stmt = scope_to_tenant(stmt, Registration, tenant_id)
    obj = db.execute(stmt).scalar_one_or_none()
    if obj is None:
        raise NotFoundError("Registration not found")
    return obj


def create_registration(
    db: Session,
    event_id: uuid.UUID,
    data: RegistrationCreate,
    *,
    tenant_id: uuid.UUID | None,
) -> Registration:
    event = get_event(db, event_id, tenant_id=tenant_id)
    tournament = get_tournament_for_event(db, event, tenant_id=tenant_id)
    if tournament.status != TournamentStatus.registration_open:
        raise ValidationError(
            "Registration is only open while the tournament status is "
            "'registration_open' (currently "
            f"'{tournament.status.value}')"
        )
    category = db.execute(
        select(EventCategory).where(EventCategory.id == event.category_id)
    ).scalar_one()

    player = _get_active_player(db, data.player_id, event.federation_id)
    partner = None
    if category.discipline == Discipline.doubles:
        if data.partner_player_id is None:
            raise ValidationError(f"'{category.name}' requires a doubles partner")
        if data.partner_player_id == data.player_id:
            raise ValidationError("A player cannot partner with themselves")
        partner = _get_active_player(db, data.partner_player_id, event.federation_id)
        _check_age_eligibility(partner, category)
    elif data.partner_player_id is not None:
        raise ValidationError(f"'{category.name}' is a singles event and cannot take a partner")

    _check_age_eligibility(player, category)
    _check_gender_scope(player, partner, category)

    obj = Registration(
        federation_id=event.federation_id,
        event_id=event.id,
        player_id=player.id,
        partner_player_id=partner.id if partner else None,
        seed=data.seed,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(f"{player.full_name} is already registered for this event") from exc
    db.refresh(obj)
    return obj


def registration_detail(db: Session, registration: Registration) -> dict:
    player = db.execute(
        select(Player.full_name).where(Player.id == registration.player_id)
    ).scalar_one_or_none()
    partner_name = None
    if registration.partner_player_id:
        partner_name = db.execute(
            select(Player.full_name).where(Player.id == registration.partner_player_id)
        ).scalar_one_or_none()
    return {"player_name": player, "partner_name": partner_name}


def update_registration(
    db: Session,
    registration_id: uuid.UUID,
    data: RegistrationUpdate,
    *,
    tenant_id: uuid.UUID | None,
) -> Registration:
    obj = get_registration(db, registration_id, tenant_id=tenant_id)
    event = get_event(db, obj.event_id, tenant_id=tenant_id)
    if event.draw_size and "seed" in data.model_dump(exclude_unset=True):
        raise ValidationError("Cannot change seed after the draw has been generated")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_registration(
    db: Session, registration_id: uuid.UUID, *, tenant_id: uuid.UUID | None
) -> None:
    obj = get_registration(db, registration_id, tenant_id=tenant_id)
    event = get_event(db, obj.event_id, tenant_id=tenant_id)
    if event.draw_size:
        raise ValidationError("Cannot withdraw a registration after the draw has been generated")
    obj.deleted_at = datetime.now(UTC)
    obj.status = RegistrationStatus.withdrawn
    db.commit()
