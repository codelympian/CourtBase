"""Ranking engine tables: rules, points, rankings, history."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import GUID, JSONType
from app.models.enums import RankingSource, TournamentLevel, enum_col
from app.models.mixins import (
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class RankingRule(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "ranking_rules"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    level: Mapped[TournamentLevel] = mapped_column(enum_col(TournamentLevel), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("event_categories.id", ondelete="SET NULL")
    )
    config: Mapped[dict | None] = mapped_column(JSONType())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RankingPoint(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """Points awarded for a result within a rule, e.g. winner=5000."""

    __tablename__ = "ranking_points"
    __table_args__ = (
        UniqueConstraint("rule_id", "result_key", name="uq_points_rule_result"),
    )

    rule_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("ranking_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # winner | runner_up | semi_final | quarter_final | round_16 | round_32 | ...
    result_key: Mapped[str] = mapped_column(String(40), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Ranking(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "rankings"
    __table_args__ = (
        UniqueConstraint(
            "federation_id", "player_id", "category_id", "as_of",
            name="uq_ranking_player_category_date",
        ),
    )

    player_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("event_categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    previous_rank: Mapped[int | None] = mapped_column(Integer)
    as_of: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[RankingSource] = mapped_column(
        enum_col(RankingSource), default=RankingSource.computed, nullable=False
    )


class RankingHistory(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """Append-only log of every ranking change."""

    __tablename__ = "ranking_history"

    player_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("event_categories.id", ondelete="CASCADE"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_rank: Mapped[int | None] = mapped_column(Integer)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    movement: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
