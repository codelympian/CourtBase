"""Schemas for clubs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class ClubBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    state_id: uuid.UUID | None = None
    coach_name: str | None = Field(default=None, max_length=200)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=400)
    logo_url: str | None = Field(default=None, max_length=500)


class ClubCreate(ClubBase):
    federation_id: uuid.UUID | None = None


class ClubUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    state_id: uuid.UUID | None = None
    coach_name: str | None = Field(default=None, max_length=200)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=400)
    logo_url: str | None = Field(default=None, max_length=500)


class ClubRead(ORMModel):
    id: uuid.UUID
    federation_id: uuid.UUID
    state_id: uuid.UUID | None
    name: str
    coach_name: str | None
    contact_email: str | None
    contact_phone: str | None
    address: str | None
    logo_url: str | None
    created_at: datetime
    updated_at: datetime


class ClubReadDetail(ClubRead):
    state_name: str | None = None
    player_count: int = 0
