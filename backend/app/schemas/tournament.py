"""Schemas for tournaments, event categories, and events."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import Discipline, EventStatus, GenderScope, TournamentLevel, TournamentStatus
from app.schemas.common import ORMModel

# ---------------------------------------------------------------- tournaments


class TournamentBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    venue: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    level: TournamentLevel
    organizer: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _check_dates(self) -> TournamentBase:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class TournamentCreate(TournamentBase):
    federation_id: uuid.UUID | None = None


class TournamentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    venue: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    level: TournamentLevel | None = None
    status: TournamentStatus | None = None
    organizer: str | None = Field(default=None, max_length=200)


class TournamentRead(ORMModel):
    id: uuid.UUID
    federation_id: uuid.UUID
    name: str
    venue: str | None
    start_date: date | None
    end_date: date | None
    level: TournamentLevel
    status: TournamentStatus
    organizer: str | None
    created_at: datetime
    updated_at: datetime


class TournamentReadDetail(TournamentRead):
    event_count: int = 0


# ------------------------------------------------------------- event categories


class EventCategoryBase(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=120)
    discipline: Discipline
    gender_scope: GenderScope = GenderScope.any
    age_min: int | None = Field(default=None, ge=0, le=120)
    age_max: int | None = Field(default=None, ge=0, le=120)

    @model_validator(mode="after")
    def _check_ages(self) -> EventCategoryBase:
        if self.age_min is not None and self.age_max is not None and self.age_min > self.age_max:
            raise ValueError("age_min cannot exceed age_max")
        return self


class EventCategoryCreate(EventCategoryBase):
    # None = a global default category (platform-wide, super admin only).
    federation_id: uuid.UUID | None = None


class EventCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    gender_scope: GenderScope | None = None
    age_min: int | None = Field(default=None, ge=0, le=120)
    age_max: int | None = Field(default=None, ge=0, le=120)
    is_active: bool | None = None


class EventCategoryRead(ORMModel):
    id: uuid.UUID
    federation_id: uuid.UUID | None
    code: str
    name: str
    discipline: Discipline
    gender_scope: GenderScope
    age_min: int | None
    age_max: int | None
    is_active: bool


# ---------------------------------------------------------------------- events


class EventCreate(BaseModel):
    category_id: uuid.UUID
    name: str | None = Field(default=None, max_length=150)


class EventUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=150)


class EventRead(ORMModel):
    id: uuid.UUID
    federation_id: uuid.UUID
    tournament_id: uuid.UUID
    category_id: uuid.UUID
    name: str
    draw_size: int | None
    status: EventStatus
    created_at: datetime
    updated_at: datetime


class EventReadDetail(EventRead):
    category_name: str | None = None
    registration_count: int = 0
