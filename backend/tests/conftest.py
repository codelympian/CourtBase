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
