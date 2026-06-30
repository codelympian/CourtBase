"""Notifications (future-ready: email / SMS / push)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import GUID, JSONType
from app.models.enums import NotificationChannel, NotificationStatus, enum_col
from app.models.mixins import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Notification(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        enum_col(NotificationChannel), nullable=False
    )
    template: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONType())
    status: Mapped[NotificationStatus] = mapped_column(
        enum_col(NotificationStatus), default=NotificationStatus.queued, nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
