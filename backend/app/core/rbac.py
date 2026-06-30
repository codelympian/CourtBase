"""Role-based access control: permission catalogue and role mappings."""

from __future__ import annotations

from app.models.enums import RoleName


class Permission:
    """Stringly-typed permission constants (``resource:action``)."""

    # System / platform
    MANAGE_USERS = "users:manage"
    MANAGE_SYSTEM = "system:manage"
    MANAGE_RANKING_RULES = "ranking_rules:manage"

    # Federation operations
    MANAGE_TOURNAMENTS = "tournaments:manage"
    MANAGE_CLUBS = "clubs:manage"
    MANAGE_STATES = "states:manage"
    MANAGE_PLAYERS = "players:manage"
    IMPORT_PLAYERS = "players:import"
    EXPORT_REPORTS = "reports:export"
    APPROVE_RANKINGS = "rankings:approve"

    # Tournament officiating
    MANAGE_DRAWS = "draws:manage"
    ENTER_SCORES = "scores:enter"
    FINALIZE_TOURNAMENTS = "tournaments:finalize"

    # Club scope
    MANAGE_OWN_CLUB_PLAYERS = "club_players:manage"
    VIEW_CLUB_STATS = "club_stats:view"

    # Self / public
    VIEW_OWN_PROFILE = "profile:view"
    VIEW_PUBLIC = "public:view"


# Role → granted permissions. Higher roles inherit lower-role capabilities explicitly.
ROLE_PERMISSIONS: dict[str, set[str]] = {
    RoleName.super_admin.value: {
        v for k, v in vars(Permission).items() if not k.startswith("_") and isinstance(v, str)
    },
    RoleName.federation_admin.value: {
        Permission.MANAGE_TOURNAMENTS,
        Permission.MANAGE_CLUBS,
        Permission.MANAGE_STATES,
        Permission.MANAGE_PLAYERS,
        Permission.IMPORT_PLAYERS,
        Permission.EXPORT_REPORTS,
        Permission.APPROVE_RANKINGS,
        Permission.MANAGE_DRAWS,
        Permission.ENTER_SCORES,
        Permission.FINALIZE_TOURNAMENTS,
        Permission.MANAGE_OWN_CLUB_PLAYERS,
        Permission.VIEW_CLUB_STATS,
        Permission.VIEW_OWN_PROFILE,
        Permission.VIEW_PUBLIC,
    },
    RoleName.tournament_official.value: {
        Permission.MANAGE_DRAWS,
        Permission.ENTER_SCORES,
        Permission.FINALIZE_TOURNAMENTS,
        Permission.VIEW_OWN_PROFILE,
        Permission.VIEW_PUBLIC,
    },
    RoleName.club_admin.value: {
        Permission.MANAGE_OWN_CLUB_PLAYERS,
        Permission.VIEW_CLUB_STATS,
        Permission.VIEW_OWN_PROFILE,
        Permission.VIEW_PUBLIC,
    },
    RoleName.player.value: {
        Permission.VIEW_OWN_PROFILE,
        Permission.VIEW_PUBLIC,
    },
    RoleName.public.value: {
        Permission.VIEW_PUBLIC,
    },
}


def permissions_for_roles(role_names: list[str]) -> set[str]:
    perms: set[str] = set()
    for name in role_names:
        perms |= ROLE_PERMISSIONS.get(name, set())
    return perms


def has_permission(role_names: list[str], permission: str) -> bool:
    return permission in permissions_for_roles(role_names)
