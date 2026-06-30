"""Event registrations."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import GUID
from app.models.enums import RegistrationStatus, enum_col
from app.models.mixins import (
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Registration(
    UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin, Base
):
    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint("event_id", "player_id", name="uq_registration_event_player"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Doubles partner (nullable for singles).
    partner_player_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("players.id", ondelete="SET NULL")
    )
    seed: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[RegistrationStatus] = mapped_column(
        enum_col(RegistrationStatus), default=RegistrationStatus.pending, nullable=False
    )
