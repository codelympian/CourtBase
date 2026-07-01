"""Pytest fixtures: isolated SQLite database + FastAPI test client."""

from __future__ import annotations

import os
import tempfile

import pytest

# Configure the environment BEFORE importing the app, so settings pick it up.
_DB_FD, _DB_PATH = tempfile.mkstemp(suffix=".sqlite3")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_DB_PATH}"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["ENVIRONMENT"] = "development"
os.environ["RATE_LIMIT_AUTH"] = "1000/minute"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.models.enums import RoleName  # noqa: E402
from app.models.role import Role  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    Base.metadata.create_all(bind=engine)
    limiter.enabled = False  # don't rate-limit during tests
    yield
    Base.metadata.drop_all(bind=engine)
    os.close(_DB_FD)
    try:
        os.remove(_DB_PATH)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def _seed_roles():
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        for role_name in RoleName:
            if not db.query(Role).filter(Role.name == role_name.value).first():
                db.add(Role(name=role_name.value))
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def admin_ctx(client):
    """A federation + a logged-in federation_admin. Returns an object with
    ``.client``, ``.headers`` (Bearer), and ``.federation_id``."""
    import uuid
    from types import SimpleNamespace

    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.enums import RoleName
    from app.models.federation import Federation
    from app.models.role import Role
    from app.models.user import User

    db = SessionLocal()
    try:
        slug = f"fed-{uuid.uuid4().hex[:8]}"
        fed = Federation(name=f"Fed {slug}", slug=slug, is_active=True)
        db.add(fed)
        db.commit()
        db.refresh(fed)

        role = db.query(Role).filter(Role.name == RoleName.federation_admin.value).first()
        email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
        password = "Adm1nPass!"
        user = User(
            federation_id=fed.id,
            email=email,
            hashed_password=hash_password(password),
            full_name="Fed Admin",
            is_active=True,
            roles=[role],
        )
        db.add(user)
        db.commit()
        fed_id = str(fed.id)
    finally:
        db.close()

    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = resp.json()["access_token"]
    return SimpleNamespace(
        client=client,
        headers={"Authorization": f"Bearer {token}"},
        federation_id=fed_id,
    )
