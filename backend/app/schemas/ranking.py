"""Schemas for the ranking engine: rules, points, standings, history."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import RankingSource, TournamentLevel
from app.schemas.common import ORMModel

# ------------------------------------------------------------- rules & points


class RankingPointInput(BaseModel):
    result_key: str = Field(min_length=1, max_length=40)
    points: int = Field(ge=0)


class RankingPointRead(ORMModel):
    id: uuid.UUID
    result_key: str
    points: int


class RankingRuleBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    level: TournamentLevel
    category_id: uuid.UUID | None = None


class RankingRuleCreate(RankingRuleBase):
    federation_id: uuid.UUID | None = None
    points: list[RankingPointInput] = Field(default_factory=list)


class RankingRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    level: TournamentLevel | None = None
    category_id: uuid.UUID | None = None
    is_active: bool | None = None
    # When provided, replaces the entire points table for this rule.
    points: list[RankingPointInput] | None = None


class RankingRuleRead(ORMModel):
    id: uuid.UUID
    federation_id: uuid.UUID
    name: str
    level: TournamentLevel
    category_id: uuid.UUID | None
    is_active: bool
    points: list[RankingPointRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------- standings


class RankingRead(ORMModel):
    id: uuid.UUID
    federation_id: uuid.UUID
    player_id: uuid.UUID
    category_id: uuid.UUID
    points: int
    rank: int
    previous_rank: int | None
    movement: int = 0
    as_of: date
    is_published: bool
    source: RankingSource


class RankingRow(RankingRead):
    """A standings row enriched with display names."""

    player_name: str | None = None
    club_name: str | None = None
    category_name: str | None = None


class RankingHistoryRead(ORMModel):
    id: uuid.UUID
    player_id: uuid.UUID
    category_id: uuid.UUID
    rank: int
    previous_rank: int | None
    points: int
    movement: int
    reason: str | None
    snapshot_date: date


# ----------------------------------------------------------------- actions


class RecalculateRequest(BaseModel):
    category_id: uuid.UUID | None = None  # None = every category with awards


class PublishRequest(BaseModel):
    category_id: uuid.UUID | None = None
    as_of: date | None = None  # None = latest snapshot per category


class RankingActionResult(BaseModel):
    categories: int
    players: int
    as_of: date
