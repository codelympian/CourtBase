"""Shared helpers for tenant-scoped CRUD services."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.services.errors import ValidationError

MAX_PAGE_SIZE = 100


def resolve_write_federation(
    user_federation_id: uuid.UUID | None, body_federation_id: uuid.UUID | None
) -> uuid.UUID:
    """Determine the federation a new row belongs to.

    - Tenant-bound users always write into their own federation.
    - Platform super admins (no federation) must specify one explicitly.
    """
    if user_federation_id is not None:
        return user_federation_id
    if body_federation_id is None:
        raise ValidationError(
            "federation_id is required for platform super admins"
        )
    return body_federation_id


def scope_to_tenant(stmt: Select, model, tenant_id: uuid.UUID | None) -> Select:
    """Filter a statement to a federation. ``None`` means unscoped (super admin)."""
    if tenant_id is not None:
        stmt = stmt.where(model.federation_id == tenant_id)
    return stmt


def paginate(db: Session, stmt: Select, page: int, size: int) -> tuple[list, int]:
    """Return ``(items, total)`` for a select statement."""
    size = max(1, min(size, MAX_PAGE_SIZE))
    page = max(1, page)
    total = db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()
    items = list(
        db.execute(stmt.offset((page - 1) * size).limit(size)).scalars().all()
    )
    return items, total
