"""Knockout draw generation and bracket advancement.

Builds a standard single-elimination bracket: seeded players are placed at the
conventional seed slots (seed 1 and seed 2 are on opposite halves, etc.), byes
are handed to the strongest remaining slots when the field isn't a power of
two, and the rest of the field is placed at random. Winners (including byes)
are then propagated forward through the bracket automatically.
"""

from __future__ import annotations

import math
import random
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import EventStatus, MatchStatus, RegistrationStatus
from app.models.match import Match
from app.models.registration import Registration
from app.models.tournament import Event
from app.services.errors import ValidationError

ROUND_NAMES = {
    1: "Final",
    2: "Semi-final",
    4: "Quarter-final",
    8: "Round of 16",
    16: "Round of 32",
    32: "Round of 64",
}


def round_name(matches_in_round: int) -> str:
    return ROUND_NAMES.get(matches_in_round, f"Round of {matches_in_round * 2}")


def _seed_slots(draw_size: int) -> list[int]:
    """Standard bracket seed order: ``result[slot_index]`` = seed number (1-based)
    that belongs at that slot, so top seeds are maximally separated."""

    def build(n: int) -> list[int]:
        if n == 1:
            return [1]
        prev = build(n // 2)
        out: list[int] = []
        for s in prev:
            out.append(s)
            out.append(n + 1 - s)
        return out

    return build(draw_size)


def _next_power_of_two(n: int) -> int:
    return 1 if n <= 1 else 2 ** math.ceil(math.log2(n))


def generate_draw(
    db: Session, event: Event, *, rng: random.Random | None = None
) -> list[Match]:
    """Generate the knockout bracket for ``event``. Raises ``ValidationError`` if
    a draw already exists or there are fewer than 2 confirmed registrations."""
    if event.draw_size:
        raise ValidationError("A draw has already been generated for this event")

    registrations = list(
        db.execute(
            select(Registration).where(
                Registration.event_id == event.id,
                Registration.deleted_at.is_(None),
                Registration.status == RegistrationStatus.confirmed,
            )
        )
        .scalars()
        .all()
    )
    if len(registrations) < 2:
        raise ValidationError(
            "At least 2 confirmed registrations are required to generate a draw"
        )

    draw_size = _next_power_of_two(len(registrations))
    seed_order = _seed_slots(draw_size)  # slot index -> seed number

    seeded = {r.seed: r for r in registrations if r.seed}
    unseeded = [r for r in registrations if not r.seed]
    (rng or random).shuffle(unseeded)

    slots: list[Registration | None] = [None] * draw_size
    for slot_idx, seed_no in enumerate(seed_order):
        reg = seeded.pop(seed_no, None)
        if reg is not None:
            slots[slot_idx] = reg
    # Any seed numbers that don't correspond to a real registration are ignored
    # (e.g. a stale seed higher than the field) — those players fall back to
    # the unseeded pool below.
    unseeded = list(seeded.values()) + unseeded

    # Fill remaining slots with unseeded players, prioritising the strongest
    # slots (lowest seed_order value) first — any leftover slots become byes.
    empty_slots = sorted(
        (i for i in range(draw_size) if slots[i] is None), key=lambda i: seed_order[i]
    )
    for slot_idx in empty_slots:
        slots[slot_idx] = unseeded.pop(0) if unseeded else None

    # ---- build round 1 matches ----
    matches_by_round: list[list[Match]] = []
    round1: list[Match] = []
    for pos in range(draw_size // 2):
        r1, r2 = slots[2 * pos], slots[2 * pos + 1]
        m = Match(
            federation_id=event.federation_id,
            event_id=event.id,
            round=1,
            position=pos,
            player1_id=r1.player_id if r1 else None,
            player2_id=r2.player_id if r2 else None,
        )
        _apply_bye_if_needed(m)
        round1.append(m)
    matches_by_round.append(round1)
    db.add_all(round1)
    db.flush()

    # ---- build subsequent rounds, linking next_match_id, propagating byes ----
    current = round1
    round_no = 1
    while len(current) > 1:
        round_no += 1
        nxt: list[Match] = []
        for pos in range(len(current) // 2):
            m = Match(
                federation_id=event.federation_id,
                event_id=event.id,
                round=round_no,
                position=pos,
            )
            nxt.append(m)
        db.add_all(nxt)
        db.flush()
        for i, child in enumerate(current):
            parent = nxt[i // 2]
            child.next_match_id = parent.id
            # Propagate a bye's winner immediately (round 1 byes are the common
            # case, but this also handles a bye-vs-bye cascade in tiny draws).
            if child.winner_id is not None:
                if child.position % 2 == 0:
                    parent.player1_id = child.winner_id
                else:
                    parent.player2_id = child.winner_id
        for m in nxt:
            _apply_bye_if_needed(m)
        db.flush()
        matches_by_round.append(nxt)
        current = nxt

    event.draw_size = draw_size
    event.status = EventStatus.draw_published
    db.commit()
    return [m for round_ in matches_by_round for m in round_]


def _apply_bye_if_needed(match: Match) -> None:
    has1, has2 = match.player1_id is not None, match.player2_id is not None
    if has1 and not has2:
        match.status = MatchStatus.bye
        match.winner_id = match.player1_id
    elif has2 and not has1:
        match.status = MatchStatus.bye
        match.winner_id = match.player2_id


def advance_winner(db: Session, match: Match) -> Match | None:
    """After a match is decided, push its winner into the next round's slot.

    Called by the match-scoring flow (not during generation, which handles its
    own bye cascade inline). Returns the updated next match, if any.
    """
    if match.next_match_id is None or match.winner_id is None:
        return None
    parent = db.get(Match, match.next_match_id)
    if parent is None:
        return None
    if match.position % 2 == 0:
        parent.player1_id = match.winner_id
    else:
        parent.player2_id = match.winner_id
    db.commit()
    db.refresh(parent)
    return parent


def get_bracket(db: Session, event_id: uuid.UUID) -> list[Match]:
    stmt = (
        select(Match)
        .where(Match.event_id == event_id, Match.deleted_at.is_(None))
        .order_by(Match.round, Match.position)
    )
    return list(db.execute(stmt).scalars().all())


def reset_draw(db: Session, event: Event) -> None:
    """Delete the generated bracket and return the event to `pending`.

    Only allowed before any score has been entered (i.e. no match is
    `completed` or `walkover` — `bye` matches don't count since those were
    never actually played).
    """
    matches = get_bracket(db, event.id)
    if any(m.status in (MatchStatus.completed, MatchStatus.walkover) for m in matches):
        raise ValidationError(
            "Cannot reset the draw: scores have already been recorded for this event"
        )
    for m in matches:
        db.delete(m)
    event.draw_size = None
    event.status = EventStatus.pending
    db.commit()
