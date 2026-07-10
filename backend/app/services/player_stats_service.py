"""Recompute player statistics from match results.

Stats are a denormalised read-model keyed by (player, category), plus an
``overall`` row (category NULL) aggregating across categories. They are rebuilt
from scratch on tournament finalize, so the operation is idempotent.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.registration import Registration
from app.models.stats import PlayerStats
from app.models.tournament import Event
from app.services import draw_service
from app.utils.ranking import compute_event_results

# Results that count as reaching each milestone.
_TITLE = {"winner"}
_FINAL = {"winner", "runner_up"}
_SEMI = {"winner", "runner_up", "semi_final"}


@dataclass
class _Acc:
    matches_played: int = 0
    wins: int = 0
    losses: int = 0
    titles: int = 0
    finals: int = 0
    semi_finals: int = 0


def _blank() -> _Acc:
    return _Acc()


def _event_partner_map(db: Session, event_id: uuid.UUID) -> dict[uuid.UUID, uuid.UUID]:
    rows = db.execute(
        select(Registration.player_id, Registration.partner_player_id).where(
            Registration.event_id == event_id,
            Registration.deleted_at.is_(None),
            Registration.partner_player_id.isnot(None),
        )
    ).all()
    return {pid: partner for pid, partner in rows}


def _accumulate_event(
    db: Session,
    event: Event,
    by_category: dict,
    overall: dict,
) -> None:
    matches = draw_service.get_bracket(db, event.id)
    if not matches:
        return
    partners = _event_partner_map(db, event.id)
    cat = event.category_id

    def bump(player_id, **deltas):
        for target in (by_category[cat][player_id], overall[player_id]):
            for k, v in deltas.items():
                setattr(target, k, getattr(target, k) + v)

    # Match wins/losses (byes don't count as played matches).
    for m in matches:
        if m.status not in (MatchStatus.completed, MatchStatus.walkover):
            continue
        for slot in (m.player1_id, m.player2_id):
            if slot is None:
                continue
            team = [slot] + ([partners[slot]] if slot in partners else [])
            won = m.winner_id == slot
            for pid in team:
                bump(pid, matches_played=1, wins=1 if won else 0, losses=0 if won else 1)

    # Milestones from finishing result.
    for player_id, result_key in compute_event_results(matches).items():
        team = [player_id] + ([partners[player_id]] if player_id in partners else [])
        for pid in team:
            bump(
                pid,
                titles=1 if result_key in _TITLE else 0,
                finals=1 if result_key in _FINAL else 0,
                semi_finals=1 if result_key in _SEMI else 0,
            )


def recompute_for_tournament(db: Session, tournament_id: uuid.UUID) -> int:
    """Rebuild PlayerStats for every player who appears in this tournament.

    Aggregates across *all* the player's completed events federation-wide (not
    just this tournament) so the stored totals stay correct and idempotent.
    """
    events = list(
        db.execute(
            select(Event).where(
                Event.tournament_id == tournament_id, Event.deleted_at.is_(None)
            )
        )
        .scalars()
        .all()
    )
    if not events:
        return 0
    federation_id = events[0].federation_id

    # Find every player involved in this tournament, then rebuild their totals
    # from all their events across the federation.
    player_ids = _players_in_tournament(db, tournament_id)
    if not player_ids:
        return 0

    all_events = list(
        db.execute(
            select(Event)
            .join(Match, Match.event_id == Event.id)
            .where(
                Event.federation_id == federation_id,
                Event.deleted_at.is_(None),
                Match.player1_id.in_(player_ids) | Match.player2_id.in_(player_ids),
            )
            .distinct()
        )
        .scalars()
        .all()
    )

    by_category: dict = defaultdict(lambda: defaultdict(_blank))
    overall: dict = defaultdict(_blank)
    for event in all_events:
        _accumulate_event(db, event, by_category, overall)

    # Only persist stats for players in this tournament (bounded write set).
    target = set(player_ids)
    _persist(db, federation_id, by_category, overall, target)
    db.commit()
    return len(target)


def _players_in_tournament(db: Session, tournament_id: uuid.UUID) -> list[uuid.UUID]:
    rows = db.execute(
        select(Registration.player_id, Registration.partner_player_id)
        .join(Event, Event.id == Registration.event_id)
        .where(
            Event.tournament_id == tournament_id,
            Registration.deleted_at.is_(None),
        )
    ).all()
    ids: set[uuid.UUID] = set()
    for pid, partner in rows:
        ids.add(pid)
        if partner:
            ids.add(partner)
    return list(ids)


def _persist(
    db: Session,
    federation_id: uuid.UUID,
    by_category: dict,
    overall: dict,
    target: set,
) -> None:
    def upsert(player_id, category_id, acc: _Acc):
        played = acc.matches_played
        win_pct = round(acc.wins / played * 100, 1) if played else 0.0
        row = db.execute(
            select(PlayerStats).where(
                PlayerStats.player_id == player_id,
                PlayerStats.category_id.is_(None)
                if category_id is None
                else PlayerStats.category_id == category_id,
            )
        ).scalar_one_or_none()
        if row is None:
            row = PlayerStats(
                federation_id=federation_id,
                player_id=player_id,
                category_id=category_id,
            )
            db.add(row)
        row.matches_played = played
        row.wins = acc.wins
        row.losses = acc.losses
        row.titles = acc.titles
        row.finals = acc.finals
        row.semi_finals = acc.semi_finals
        row.win_percentage = win_pct

    for cat, players in by_category.items():
        for pid, acc in players.items():
            if pid in target:
                upsert(pid, cat, acc)
    for pid, acc in overall.items():
        if pid in target:
            upsert(pid, None, acc)
