"""The ranking engine: award points, recalculate standings, history, publish.

Points live in an append-only ledger (``ranking_awards``); a player's total for a
category is the sum of their awards (imported baseline + tournament results).
``rankings`` is a derived, dated snapshot; ``ranking_history`` is the audit trail.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import RankingSource
from app.models.player import Player
from app.models.ranking import Ranking, RankingAward, RankingHistory
from app.models.registration import Registration
from app.models.stats import PlayerStats
from app.models.tournament import Event, EventCategory, Tournament
from app.services import draw_service, ranking_rule_service
from app.utils.ranking import compute_event_results

# ------------------------------------------------------------------ awarding


def _event_partner_map(db: Session, event_id: uuid.UUID) -> dict[uuid.UUID, uuid.UUID]:
    """player_id -> partner_player_id for doubles registrations in an event."""
    rows = db.execute(
        select(Registration.player_id, Registration.partner_player_id).where(
            Registration.event_id == event_id,
            Registration.deleted_at.is_(None),
            Registration.partner_player_id.isnot(None),
        )
    ).all()
    return {pid: partner for pid, partner in rows}


def award_tournament(db: Session, tournament: Tournament) -> int:
    """(Re)award ranking points for every completed event in a tournament.

    Idempotent: existing awards for this tournament are removed first, so
    re-finalizing never double-counts. Returns the number of award rows created.
    """
    db.execute(
        RankingAward.__table__.delete().where(
            RankingAward.tournament_id == tournament.id
        )
    )

    awarded_on = tournament.end_date or date.today()
    events = list(
        db.execute(
            select(Event).where(
                Event.tournament_id == tournament.id, Event.deleted_at.is_(None)
            )
        )
        .scalars()
        .all()
    )

    created = 0
    for event in events:
        rule = ranking_rule_service.resolve_rule_for_event(
            db,
            federation_id=tournament.federation_id,
            level=tournament.level,
            category_id=event.category_id,
        )
        if rule is None:
            continue  # no points configured for this level/category
        pmap = ranking_rule_service.points_map(db, rule)
        matches = draw_service.get_bracket(db, event.id)
        if not matches:
            continue
        results = compute_event_results(matches)
        partners = _event_partner_map(db, event.id)

        for player_id, result_key in results.items():
            points = pmap.get(result_key, 0)
            if points <= 0:
                continue
            recipients = [player_id]
            if player_id in partners:
                recipients.append(partners[player_id])
            for pid in recipients:
                db.add(
                    RankingAward(
                        federation_id=tournament.federation_id,
                        player_id=pid,
                        category_id=event.category_id,
                        points=points,
                        source=RankingSource.computed,
                        tournament_id=tournament.id,
                        event_id=event.id,
                        result_key=result_key,
                        reason=f"{tournament.name}: {result_key.replace('_', ' ')}",
                        awarded_on=awarded_on,
                    )
                )
                created += 1
    db.commit()
    return created


def import_baseline(
    db: Session,
    *,
    federation_id: uuid.UUID,
    category_id: uuid.UUID,
    player_id: uuid.UUID,
    points: int,
    awarded_on: date | None = None,
) -> RankingAward:
    """Record an imported baseline award (the initial ranking from migration).

    Replaces any prior imported baseline for this player/category so re-imports
    are idempotent; tournament awards are left untouched.
    """
    db.execute(
        RankingAward.__table__.delete().where(
            RankingAward.federation_id == federation_id,
            RankingAward.category_id == category_id,
            RankingAward.player_id == player_id,
            RankingAward.source == RankingSource.imported,
        )
    )
    award = RankingAward(
        federation_id=federation_id,
        player_id=player_id,
        category_id=category_id,
        points=points,
        source=RankingSource.imported,
        result_key="baseline",
        reason="Imported baseline ranking",
        awarded_on=awarded_on or date.today(),
    )
    db.add(award)
    db.commit()
    return award


# --------------------------------------------------------------- recalculate


def _categories_with_awards(db: Session, federation_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.execute(
            select(RankingAward.category_id)
            .where(RankingAward.federation_id == federation_id)
            .distinct()
        )
        .scalars()
        .all()
    )


def _totals(
    db: Session, federation_id: uuid.UUID, category_id: uuid.UUID
) -> dict[uuid.UUID, int]:
    rows = db.execute(
        select(RankingAward.player_id, func.sum(RankingAward.points))
        .where(
            RankingAward.federation_id == federation_id,
            RankingAward.category_id == category_id,
        )
        .group_by(RankingAward.player_id)
    ).all()
    return {pid: int(total or 0) for pid, total in rows}


def _tiebreak_data(
    db: Session, category_id: uuid.UUID, player_ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple]:
    """(-titles, -finals, -semi_finals, name) sort key tail per player."""
    if not player_ids:
        return {}
    stats = {
        pid: (titles, finals, sfs)
        for pid, titles, finals, sfs in db.execute(
            select(
                PlayerStats.player_id,
                PlayerStats.titles,
                PlayerStats.finals,
                PlayerStats.semi_finals,
            ).where(
                PlayerStats.category_id == category_id,
                PlayerStats.player_id.in_(player_ids),
            )
        ).all()
    }
    names = dict(
        db.execute(
            select(Player.id, Player.full_name).where(Player.id.in_(player_ids))
        ).all()
    )
    out: dict[uuid.UUID, tuple] = {}
    for pid in player_ids:
        titles, finals, sfs = stats.get(pid, (0, 0, 0))
        out[pid] = (-titles, -finals, -sfs, (names.get(pid) or "").lower())
    return out


def _previous_ranks(
    db: Session, federation_id: uuid.UUID, category_id: uuid.UUID, before: date
) -> dict[uuid.UUID, int]:
    """Rank of each player in the most recent snapshot strictly before ``before``."""
    last = db.execute(
        select(func.max(Ranking.as_of)).where(
            Ranking.federation_id == federation_id,
            Ranking.category_id == category_id,
            Ranking.as_of < before,
        )
    ).scalar_one_or_none()
    if last is None:
        return {}
    rows = db.execute(
        select(Ranking.player_id, Ranking.rank).where(
            Ranking.federation_id == federation_id,
            Ranking.category_id == category_id,
            Ranking.as_of == last,
        )
    ).all()
    return {pid: rank for pid, rank in rows}


def recalculate_category(
    db: Session,
    *,
    federation_id: uuid.UUID,
    category_id: uuid.UUID,
    as_of: date | None = None,
) -> int:
    """Rebuild the ranking snapshot for one category. Returns players ranked."""
    as_of = as_of or date.today()
    totals = _totals(db, federation_id, category_id)
    if not totals:
        return 0

    player_ids = list(totals)
    tails = _tiebreak_data(db, category_id, player_ids)
    # Sort: points desc, then titles/finals/SF desc, then name asc (deterministic).
    ordered = sorted(player_ids, key=lambda pid: (-totals[pid], *tails[pid]))
    prev = _previous_ranks(db, federation_id, category_id, as_of)

    for idx, pid in enumerate(ordered):
        rank = idx + 1
        previous_rank = prev.get(pid)
        movement = (previous_rank - rank) if previous_rank is not None else 0
        points = totals[pid]

        row = db.execute(
            select(Ranking).where(
                Ranking.federation_id == federation_id,
                Ranking.player_id == pid,
                Ranking.category_id == category_id,
                Ranking.as_of == as_of,
            )
        ).scalar_one_or_none()
        if row is None:
            row = Ranking(
                federation_id=federation_id,
                player_id=pid,
                category_id=category_id,
                as_of=as_of,
            )
            db.add(row)
        row.points = points
        row.rank = rank
        row.previous_rank = previous_rank
        row.is_published = False  # standings changed → require re-approval
        row.source = RankingSource.computed

        db.add(
            RankingHistory(
                federation_id=federation_id,
                player_id=pid,
                category_id=category_id,
                rank=rank,
                previous_rank=previous_rank,
                points=points,
                movement=movement,
                reason="recalculation",
                snapshot_date=as_of,
            )
        )
    db.commit()
    return len(ordered)


def recalculate(
    db: Session,
    *,
    federation_id: uuid.UUID,
    category_id: uuid.UUID | None = None,
    as_of: date | None = None,
) -> tuple[int, int, date]:
    """Recalculate one or all categories. Returns (categories, players, as_of)."""
    as_of = as_of or date.today()
    categories = [category_id] if category_id else _categories_with_awards(db, federation_id)
    total_players = 0
    for cid in categories:
        total_players += recalculate_category(
            db, federation_id=federation_id, category_id=cid, as_of=as_of
        )
    return len(categories), total_players, as_of


# ------------------------------------------------------------------ reads


def _latest_as_of(
    db: Session, federation_id: uuid.UUID, category_id: uuid.UUID
) -> date | None:
    return db.execute(
        select(func.max(Ranking.as_of)).where(
            Ranking.federation_id == federation_id,
            Ranking.category_id == category_id,
        )
    ).scalar_one_or_none()


def list_rankings(
    db: Session,
    *,
    federation_id: uuid.UUID,
    category_id: uuid.UUID,
    published_only: bool = False,
    as_of: date | None = None,
) -> list[dict]:
    """Current standings for a category (latest snapshot unless ``as_of`` given)."""
    as_of = as_of or _latest_as_of(db, federation_id, category_id)
    if as_of is None:
        return []
    stmt = select(Ranking).where(
        Ranking.federation_id == federation_id,
        Ranking.category_id == category_id,
        Ranking.as_of == as_of,
    )
    if published_only:
        stmt = stmt.where(Ranking.is_published.is_(True))
    rows = list(db.execute(stmt.order_by(Ranking.rank)).scalars().all())

    player_ids = [r.player_id for r in rows]
    names = dict(
        db.execute(
            select(Player.id, Player.full_name).where(Player.id.in_(player_ids))
        ).all()
    ) if player_ids else {}
    clubs = dict(
        db.execute(
            select(Player.id, Player.club_id).where(Player.id.in_(player_ids))
        ).all()
    ) if player_ids else {}
    from app.models.org import Club

    club_ids = [c for c in clubs.values() if c]
    club_names = dict(
        db.execute(select(Club.id, Club.name).where(Club.id.in_(club_ids))).all()
    ) if club_ids else {}

    out = []
    for r in rows:
        movement = (r.previous_rank - r.rank) if r.previous_rank is not None else 0
        out.append(
            {
                **{k: getattr(r, k) for k in (
                    "id", "federation_id", "player_id", "category_id",
                    "points", "rank", "previous_rank", "as_of", "is_published", "source",
                )},
                "movement": movement,
                "player_name": names.get(r.player_id),
                "club_name": club_names.get(clubs.get(r.player_id)),
            }
        )
    return out


def list_history(
    db: Session,
    *,
    federation_id: uuid.UUID,
    player_id: uuid.UUID,
    category_id: uuid.UUID | None = None,
) -> list[RankingHistory]:
    stmt = select(RankingHistory).where(
        RankingHistory.federation_id == federation_id,
        RankingHistory.player_id == player_id,
    )
    if category_id:
        stmt = stmt.where(RankingHistory.category_id == category_id)
    stmt = stmt.order_by(RankingHistory.snapshot_date, RankingHistory.created_at)
    return list(db.execute(stmt).scalars().all())


def publish(
    db: Session,
    *,
    federation_id: uuid.UUID,
    category_id: uuid.UUID,
    as_of: date | None = None,
) -> int:
    as_of = as_of or _latest_as_of(db, federation_id, category_id)
    if as_of is None:
        return 0
    rows = list(
        db.execute(
            select(Ranking).where(
                Ranking.federation_id == federation_id,
                Ranking.category_id == category_id,
                Ranking.as_of == as_of,
            )
        )
        .scalars()
        .all()
    )
    for r in rows:
        r.is_published = True
    db.commit()
    return len(rows)


def category_name(db: Session, category_id: uuid.UUID) -> str | None:
    return db.execute(
        select(EventCategory.name).where(EventCategory.id == category_id)
    ).scalar_one_or_none()
