"""Tournaments, event categories, and events."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import GUID
from app.models.enums import (
    Discipline,
    EventStatus,
    GenderScope,
    TournamentLevel,
    TournamentStatus,
    enum_col,
)
from app.models.mixins import (
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Tournament(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "tournaments"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    venue: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[date | None] = mapped_column(Date, index=True)
    end_date: Mapped[date | None] = mapped_column(Date)
    level: Mapped[TournamentLevel] = mapped_column(enum_col(TournamentLevel), nullable=False)
    status: Mapped[TournamentStatus] = mapped_column(
        enum_col(TournamentStatus), default=TournamentStatus.draft, nullable=False, index=True
    )
    organizer: Mapped[str | None] = mapped_column(String(200))
    ranking_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("ranking_rules.id", ondelete="SET NULL")
    )


class EventCategory(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Event category. ``federation_id`` NULL means a global default category."""

    __tablename__ = "event_categories"
    __table_args__ = (
        UniqueConstraint("federation_id", "code", name="uq_category_federation_code"),
    )

    federation_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("federations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    discipline: Mapped[Discipline] = mapped_column(enum_col(Discipline), nullable=False)
    gender_scope: Mapped[GenderScope] = mapped_column(
        enum_col(GenderScope), default=GenderScope.any, nullable=False
    )
    age_min: Mapped[int | None] = mapped_column(Integer)
    age_max: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Event(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("tournament_id", "category_id", name="uq_event_tournament_category"),
    )

    tournament_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("event_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    draw_size: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[EventStatus] = mapped_column(
        enum_col(EventStatus), default=EventStatus.pending, nullable=False
    )
