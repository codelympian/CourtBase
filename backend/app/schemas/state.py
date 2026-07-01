"""Schemas for state associations."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class StateBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: str | None = Field(default=None, max_length=20)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=40)


class StateCreate(StateBase):
    # Required only when the caller is a platform super admin (no fixed federation).
    federation_id: uuid.UUID | None = None


class StateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    code: str | None = Field(default=None, max_length=20)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=40)


class StateRead(ORMModel):
    id: uuid.UUID
    federation_id: uuid.UUID
    name: str
    code: str | None
    contact_email: str | None
    contact_phone: str | None
    created_at: datetime
    updated_at: datetime
