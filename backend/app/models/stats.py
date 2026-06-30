"""Player statistics read-model (recomputed from matches)."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import GUID
from app.models.mixins import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class PlayerStats(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "player_stats"
    __table_args__ = (
        UniqueConstraint("player_id", "category_id", name="uq_stats_player_category"),
    )

    player_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # NULL category = overall stats across all categories.
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("event_categories.id", ondelete="CASCADE")
    )
    matches_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    titles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    finals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    semi_finals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    win_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
