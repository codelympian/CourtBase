"""Seed baseline data: roles, a demo federation, and the bootstrap super admin.

Run with:  python -m app.seed
"""

from __future__ import annotations

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.enums import Discipline, GenderScope, RoleName, TournamentLevel
from app.models.federation import Federation
from app.models.ranking import RankingPoint, RankingRule
from app.models.role import Role
from app.models.tournament import EventCategory
from app.models.user import User

ROLE_DESCRIPTIONS = {
    RoleName.super_admin: "Platform owner: users, settings, ranking rules, configuration",
    RoleName.federation_admin: "Tournaments, players, clubs, rankings, imports, reports",
    RoleName.tournament_official: "Draws, match scores, finalizing tournaments",
    RoleName.club_admin: "Register/update own club players, view club stats",
    RoleName.player: "View own profile, rankings, tournament & match history",
    RoleName.public: "Read-only public information",
}

# Global default event categories (federation_id=None), per the spec's Senior/Junior
# lists. Federations can add further categories (e.g. gender/discipline-split junior
# events) via the Event Categories admin screen.
DEFAULT_CATEGORIES = [
    # code, name, discipline, gender_scope, age_min, age_max
    ("MS", "Men's Singles", Discipline.singles, GenderScope.men, None, None),
    ("WS", "Women's Singles", Discipline.singles, GenderScope.women, None, None),
    ("MD", "Men's Doubles", Discipline.doubles, GenderScope.men, None, None),
    ("WD", "Women's Doubles", Discipline.doubles, GenderScope.women, None, None),
    ("XD", "Mixed Doubles", Discipline.doubles, GenderScope.mixed, None, None),
    ("U11", "Under-11", Discipline.singles, GenderScope.any, None, 10),
    ("U13", "Under-13", Discipline.singles, GenderScope.any, None, 12),
    ("U15", "Under-15", Discipline.singles, GenderScope.any, None, 14),
    ("U17", "Under-17", Discipline.singles, GenderScope.any, None, 16),
    ("U19", "Under-19", Discipline.singles, GenderScope.any, None, 18),
]


def seed() -> None:
    db = SessionLocal()
    try:
        # Roles
        for role_name, desc in ROLE_DESCRIPTIONS.items():
            existing = db.execute(
                select(Role).where(Role.name == role_name.value)
            ).scalar_one_or_none()
            if not existing:
                db.add(Role(name=role_name.value, description=desc))
        db.commit()

        # Demo federation
        fed = db.execute(
            select(Federation).where(Federation.slug == "demo")
        ).scalar_one_or_none()
        if not fed:
            fed = Federation(
                name="Demo Badminton Federation",
                slug="demo",
                country="Nigeria",
                contact_email="info@demo.courtbase.dev",
                primary_color="#16a34a",
                is_active=True,
            )
            db.add(fed)
            db.commit()
            db.refresh(fed)

        # Global default event categories
        for code, name, discipline, gender_scope, age_min, age_max in DEFAULT_CATEGORIES:
            existing = db.execute(
                select(EventCategory).where(
                    EventCategory.federation_id.is_(None), EventCategory.code == code
                )
            ).scalar_one_or_none()
            if not existing:
                db.add(
                    EventCategory(
                        federation_id=None,
                        code=code,
                        name=name,
                        discipline=discipline,
                        gender_scope=gender_scope,
                        age_min=age_min,
                        age_max=age_max,
                    )
                )
        db.commit()

        # Default ranking rule for the demo federation (the spec's example).
        existing_rule = db.execute(
            select(RankingRule).where(
                RankingRule.federation_id == fed.id,
                RankingRule.level == TournamentLevel.national_championship,
                RankingRule.category_id.is_(None),
            )
        ).scalar_one_or_none()
        if not existing_rule:
            rule = RankingRule(
                federation_id=fed.id,
                name="National Championship",
                level=TournamentLevel.national_championship,
                category_id=None,
                is_active=True,
            )
            db.add(rule)
            db.flush()
            for result_key, points in (
                ("winner", 5000),
                ("runner_up", 4250),
                ("semi_final", 3500),
                ("quarter_final", 2750),
                ("round_16", 2000),
                ("round_32", 1250),
            ):
                db.add(
                    RankingPoint(
                        federation_id=fed.id,
                        rule_id=rule.id,
                        result_key=result_key,
                        points=points,
                    )
                )
            db.commit()

        # Bootstrap platform super admin
        admin = db.execute(
            select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL.lower())
        ).scalar_one_or_none()
        if not admin:
            super_role = db.execute(
                select(Role).where(Role.name == RoleName.super_admin.value)
            ).scalar_one()
            admin = User(
                email=settings.FIRST_SUPERUSER_EMAIL.lower(),
                hashed_password=hash_password(settings.FIRST_SUPERUSER_PASSWORD),
                full_name="Platform Super Admin",
                is_active=True,
                is_superuser=True,
                federation_id=None,
                roles=[super_role],
            )
            db.add(admin)
            db.commit()
            print(f"Created super admin: {admin.email}")
        else:
            print(f"Super admin already exists: {admin.email}")

        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
