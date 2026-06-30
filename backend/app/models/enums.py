"""Enumerations used across the domain models."""

from __future__ import annotations

import enum

from sqlalchemy import Enum as SAEnum


def enum_col(enum_cls: type[enum.Enum]) -> SAEnum:
    """Portable string-backed enum column with a CHECK constraint.

    ``native_enum=False`` stores the value as VARCHAR + CHECK on every dialect,
    avoiding PostgreSQL ENUM type churn in migrations while keeping validation.
    """
    return SAEnum(
        enum_cls,
        native_enum=False,
        values_callable=lambda e: [member.value for member in e],
        validate_strings=True,
        length=40,
    )


class RoleName(str, enum.Enum):
    super_admin = "super_admin"
    federation_admin = "federation_admin"
    tournament_official = "tournament_official"
    club_admin = "club_admin"
    player = "player"
    public = "public"


class Gender(str, enum.Enum):
    male = "M"
    female = "F"
    other = "O"


class PlayerStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"
    retired = "retired"


class TournamentLevel(str, enum.Enum):
    national_championship = "national_championship"
    open = "open"
    invitational = "invitational"
    ranking = "ranking"


class TournamentStatus(str, enum.Enum):
    draft = "draft"
    registration_open = "registration_open"
    registration_closed = "registration_closed"
    ongoing = "ongoing"
    completed = "completed"


class Discipline(str, enum.Enum):
    singles = "singles"
    doubles = "doubles"


class GenderScope(str, enum.Enum):
    men = "men"
    women = "women"
    mixed = "mixed"
    any = "any"


class EventStatus(str, enum.Enum):
    pending = "pending"
    draw_published = "draw_published"
    ongoing = "ongoing"
    completed = "completed"


class RegistrationStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    withdrawn = "withdrawn"
    rejected = "rejected"


class MatchStatus(str, enum.Enum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    walkover = "walkover"
    bye = "bye"


class RankingSource(str, enum.Enum):
    imported = "imported"
    computed = "computed"


class NotificationChannel(str, enum.Enum):
    email = "email"
    sms = "sms"
    push = "push"


class NotificationStatus(str, enum.Enum):
    queued = "queued"
    sent = "sent"
    failed = "failed"
