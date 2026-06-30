"""Player profiles."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import GUID
from app.models.enums import Gender, PlayerStatus, enum_col
from app.models.mixins import (
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Player(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "players"
    __table_args__ = (
        UniqueConstraint(
            "federation_id", "federation_player_code", name="uq_player_federation_code"
        ),
    )

    federation_player_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    gender: Mapped[Gender] = mapped_column(enum_col(Gender), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    nationality: Mapped[str | None] = mapped_column(String(80))
    photo_url: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[PlayerStatus] = mapped_column(
        enum_col(PlayerStatus), default=PlayerStatus.active, nullable=False, index=True
    )

    club_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("clubs.id", ondelete="SET NULL"), index=True
    )
    state_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("state_associations.id", ondelete="SET NULL"), index=True
    )

    @property
    def age(self) -> int | None:
        if not self.date_of_birth:
            return None
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )
