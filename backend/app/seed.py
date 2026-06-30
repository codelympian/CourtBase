"""Seed baseline data: roles, a demo federation, and the bootstrap super admin.

Run with:  python -m app.seed
"""

from __future__ import annotations

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.enums import RoleName
from app.models.federation import Federation
from app.models.role import Role
from app.models.user import User

ROLE_DESCRIPTIONS = {
    RoleName.super_admin: "Platform owner: users, settings, ranking rules, configuration",
    RoleName.federation_admin: "Tournaments, players, clubs, rankings, imports, reports",
    RoleName.tournament_official: "Draws, match scores, finalizing tournaments",
    RoleName.club_admin: "Register/update own club players, view club stats",
    RoleName.player: "View own profile, rankings, tournament & match history",
    RoleName.public: "Read-only public information",
}


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
