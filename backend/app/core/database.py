"""Database engine, session factory, and the declarative base."""

from __future__ import annotations

import ssl
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


def _is_local(url: str) -> bool:
    return "localhost" in url or "127.0.0.1" in url


connect_args: dict = {}
if settings.is_sqlite:
    # Needed for SQLite when used across threads (tests / dev fallback).
    connect_args = {"check_same_thread": False}
elif "+pg8000" in settings.DATABASE_URL and not _is_local(settings.DATABASE_URL):
    # Managed Postgres (e.g. Supabase) requires TLS. pg8000 needs an explicit
    # SSL context; psycopg instead takes ?sslmode=require in the URL.
    ssl_ctx = ssl.create_default_context()
    if not settings.DATABASE_SSL_VERIFY:
        # Encrypt without verifying the CA (mirrors libpq sslmode=require). The
        # Supabase pooler chain isn't in the system trust store by default.
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
    connect_args = {"ssl_context": ssl_ctx}

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Generator:
    """FastAPI dependency that yields a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
