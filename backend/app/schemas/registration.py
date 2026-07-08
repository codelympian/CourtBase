"""Schemas for event registrations."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import RegistrationStatus
from app.schemas.common import ORMModel


class RegistrationCreate(BaseModel):
    player_id: uuid.UUID
    partner_player_id: uuid.UUID | None = None
    seed: int | None = Field(default=None, ge=1)


class RegistrationUpdate(BaseModel):
    seed: int | None = Field(default=None, ge=1)
    status: RegistrationStatus | None = None


class RegistrationRead(ORMModel):
    id: uuid.UUID
    federation_id: uuid.UUID
    event_id: uuid.UUID
    player_id: uuid.UUID
    partner_player_id: uuid.UUID | None
    seed: int | None
    status: RegistrationStatus
    created_at: datetime


class RegistrationReadDetail(RegistrationRead):
    player_name: str | None = None
    partner_name: str | None = None
