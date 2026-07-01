"""Aggregate counts for the dashboard overview."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import PlayerStatus, TournamentStatus
from app.models.org import Club, StateAssociation
from app.models.player import Player
from app.models.tournament import Tournament


def _count(db: Session, model, tenant_id: uuid.UUID | None, *extra) -> int:
    stmt = select(func.count()).select_from(model).where(model.deleted_at.is_(None), *extra)
    if tenant_id is not None:
        stmt = stmt.where(model.federation_id == tenant_id)
    return db.execute(stmt).scalar_one()


def overview(db: Session, tenant_id: uuid.UUID | None) -> dict:
    active_statuses = (
        TournamentStatus.registration_open,
        TournamentStatus.registration_closed,
        TournamentStatus.ongoing,
    )
    return {
        "total_players": _count(db, Player, tenant_id),
        "active_players": _count(
            db, Player, tenant_id, Player.status == PlayerStatus.active
        ),
        "total_clubs": _count(db, Club, tenant_id),
        "total_states": _count(db, StateAssociation, tenant_id),
        "total_tournaments": _count(db, Tournament, tenant_id),
        "active_tournaments": _count(
            db, Tournament, tenant_id, Tournament.status.in_(active_statuses)
        ),
    }
