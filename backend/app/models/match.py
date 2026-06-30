"""Matches within an event bracket."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import GUID, JSONType
from app.models.enums import MatchStatus, enum_col
from app.models.mixins import (
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Match(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "matches"

    event_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    round: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    player1_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("players.id", ondelete="SET NULL")
    )
    player2_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("players.id", ondelete="SET NULL")
    )
    winner_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("players.id", ondelete="SET NULL")
    )

    # Game scores, e.g. [[21, 18], [18, 21], [21, 16]].
    score: Mapped[list | None] = mapped_column(JSONType())
    status: Mapped[MatchStatus] = mapped_column(
        enum_col(MatchStatus), default=MatchStatus.scheduled, nullable=False, index=True
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Bracket advancement: the match the winner feeds into.
    next_match_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("matches.id", ondelete="SET NULL")
    )
