"""Import all models so SQLAlchemy metadata and Alembic see every table."""

from app.models.audit import AuditLog
from app.models.enums import (
    Discipline,
    EventStatus,
    Gender,
    GenderScope,
    MatchStatus,
    NotificationChannel,
    NotificationStatus,
    PlayerStatus,
    RankingSource,
    RegistrationStatus,
    RoleName,
    TournamentLevel,
    TournamentStatus,
)
from app.models.federation import Federation
from app.models.match import Match
from app.models.notification import Notification
from app.models.org import Club, StateAssociation
from app.models.player import Player
from app.models.ranking import Ranking, RankingHistory, RankingPoint, RankingRule
from app.models.registration import Registration
from app.models.role import Role, user_roles
from app.models.stats import PlayerStats
from app.models.tournament import Event, EventCategory, Tournament
from app.models.user import RefreshToken, User

__all__ = [
    "AuditLog",
    "Club",
    "Discipline",
    "Event",
    "EventCategory",
    "EventStatus",
    "Federation",
    "Gender",
    "GenderScope",
    "Match",
    "MatchStatus",
    "Notification",
    "NotificationChannel",
    "NotificationStatus",
    "Player",
    "PlayerStats",
    "PlayerStatus",
    "Ranking",
    "RankingHistory",
    "RankingPoint",
    "RankingRule",
    "RankingSource",
    "RefreshToken",
    "Registration",
    "RegistrationStatus",
    "Role",
    "RoleName",
    "StateAssociation",
    "Tournament",
    "TournamentLevel",
    "TournamentStatus",
    "User",
    "user_roles",
]
