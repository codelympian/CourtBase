"""State associations and clubs."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import GUID
from app.models.mixins import (
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class StateAssociation(
    UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin, Base
):
    __tablename__ = "state_associations"
    __table_args__ = (
        UniqueConstraint("federation_id", "name", name="uq_state_federation_name"),
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str | None] = mapped_column(String(20))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(40))


class Club(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "clubs"
    __table_args__ = (
        UniqueConstraint("federation_id", "name", name="uq_club_federation_name"),
    )

    state_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("state_associations.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    coach_name: Mapped[str | None] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(40))
    address: Mapped[str | None] = mapped_column(String(400))
    logo_url: Mapped[str | None] = mapped_column(String(500))
