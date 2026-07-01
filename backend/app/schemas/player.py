"""Schemas for players."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import Gender, PlayerStatus
from app.schemas.common import ORMModel


class PlayerBase(BaseModel):
    federation_player_code: str = Field(min_length=1, max_length=40)
    full_name: str = Field(min_length=1, max_length=200)
    gender: Gender
    date_of_birth: date | None = None
    nationality: str | None = Field(default=None, max_length=80)
    photo_url: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    status: PlayerStatus = PlayerStatus.active
    club_id: uuid.UUID | None = None
    state_id: uuid.UUID | None = None


class PlayerCreate(PlayerBase):
    federation_id: uuid.UUID | None = None


class PlayerUpdate(BaseModel):
    federation_player_code: str | None = Field(default=None, min_length=1, max_length=40)
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    gender: Gender | None = None
    date_of_birth: date | None = None
    nationality: str | None = Field(default=None, max_length=80)
    photo_url: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    status: PlayerStatus | None = None
    club_id: uuid.UUID | None = None
    state_id: uuid.UUID | None = None


class PlayerRead(ORMModel):
    id: uuid.UUID
    federation_id: uuid.UUID
    federation_player_code: str
    full_name: str
    gender: Gender
    date_of_birth: date | None
    nationality: str | None
    photo_url: str | None
    phone: str | None
    email: str | None
    status: PlayerStatus
    club_id: uuid.UUID | None
    state_id: uuid.UUID | None
    age: int | None = None
    age_category: str | None = None
    created_at: datetime
    updated_at: datetime


class PlayerReadDetail(PlayerRead):
    club_name: str | None = None
    state_name: str | None = None


class ImportError(BaseModel):
    row: int
    message: str


class ImportResult(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: list[ImportError] = []
