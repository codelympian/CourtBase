"""Match score entry and bracket reads."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import EventStatus, MatchStatus
from app.models.match import Match
from app.models.player import Player
from app.models.tournament import Event
from app.schemas.match import MatchScoreInput
from app.services import draw_service
from app.services.crud import scope_to_tenant
from app.services.errors import NotFoundError, ValidationError
from app.utils.scoring import match_winner


def get_match(db: Session, match_id: uuid.UUID, *, tenant_id: uuid.UUID | None) -> Match:
    stmt = select(Match).where(Match.id == match_id, Match.deleted_at.is_(None))
    stmt = scope_to_tenant(stmt, Match, tenant_id)
    obj = db.execute(stmt).scalar_one_or_none()
    if obj is None:
        raise NotFoundError("Match not found")
    return obj


def match_detail(db: Session, match: Match) -> dict:
    names = dict(
        db.execute(
            select(Player.id, Player.full_name).where(
                Player.id.in_(
                    [pid for pid in (match.player1_id, match.player2_id, match.winner_id) if pid]
                )
            )
        ).all()
    )
    return {
        "player1_name": names.get(match.player1_id),
        "player2_name": names.get(match.player2_id),
        "winner_name": names.get(match.winner_id),
    }


def _mark_event_progress(db: Session, event: Event, *, just_completed_final: bool) -> None:
    if just_completed_final:
        event.status = EventStatus.completed
    elif event.status == EventStatus.draw_published:
        event.status = EventStatus.ongoing


def record_score(
    db: Session, match_id: uuid.UUID, data: MatchScoreInput, *, tenant_id: uuid.UUID | None
) -> Match:
    match = get_match(db, match_id, tenant_id=tenant_id)
    if match.status in (MatchStatus.completed, MatchStatus.walkover, MatchStatus.bye):
        raise ValidationError("This match has already been decided")
    if match.player1_id is None or match.player2_id is None:
        raise ValidationError("Both players must be known before a score can be recorded")

    if data.walkover_winner_id is not None:
        if data.walkover_winner_id not in (match.player1_id, match.player2_id):
            raise ValidationError("The walkover winner must be one of this match's players")
        match.winner_id = data.walkover_winner_id
        match.status = MatchStatus.walkover
        match.score = None
    else:
        try:
            winner_slot = match_winner(data.score or [])
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        match.winner_id = match.player1_id if winner_slot == 1 else match.player2_id
        match.status = MatchStatus.completed
        match.score = data.score

    db.commit()
    db.refresh(match)

    is_final = match.next_match_id is None
    event = db.get(Event, match.event_id)
    if event is not None:
        _mark_event_progress(db, event, just_completed_final=is_final)
        db.commit()

    draw_service.advance_winner(db, match)
    db.refresh(match)
    return match


def list_bracket(db: Session, event_id: uuid.UUID, *, tenant_id: uuid.UUID | None) -> list[Match]:
    # Validate the event is in scope, then return its full bracket.
    from app.services.event_service import get_event

    get_event(db, event_id, tenant_id=tenant_id)
    return draw_service.get_bracket(db, event_id)
