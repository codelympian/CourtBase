"""Schemas for matches, score entry, and draw generation."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, model_validator

from app.models.enums import MatchStatus
from app.schemas.common import ORMModel


class MatchRead(ORMModel):
    id: uuid.UUID
    federation_id: uuid.UUID
    event_id: uuid.UUID
    round: int
    position: int
    player1_id: uuid.UUID | None
    player2_id: uuid.UUID | None
    winner_id: uuid.UUID | None
    score: list | None
    status: MatchStatus
    scheduled_at: datetime | None
    next_match_id: uuid.UUID | None


class MatchReadDetail(MatchRead):
    player1_name: str | None = None
    player2_name: str | None = None
    winner_name: str | None = None


class MatchScoreInput(BaseModel):
    """Record a completed game score, or a walkover.

    Exactly one of ``score`` or ``walkover_winner_id`` must be provided.
    ``score`` is a list of ``[player1_points, player2_points]`` games, e.g.
    ``[[21, 18], [18, 21], [21, 16]]``.
    """

    score: list[list[int]] | None = None
    walkover_winner_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> MatchScoreInput:
        has_score = self.score is not None
        has_walkover = self.walkover_winner_id is not None
        if has_score == has_walkover:
            raise ValueError("Provide exactly one of `score` or `walkover_winner_id`")
        if has_score:
            for game in self.score or []:
                if len(game) != 2:
                    raise ValueError("Each game must be `[player1_points, player2_points]`")
        return self


class BracketMatch(MatchReadDetail):
    """A match annotated with its bracket slot label for display."""

    round_name: str = ""
