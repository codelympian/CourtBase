"""Business logic for event categories.

Categories may be global platform defaults (``federation_id`` is ``NULL``, e.g. the
seeded Senior/Junior set) or federation-specific additions. Regular federation users
always create/see their own federation's categories plus the global defaults; only
platform super admins (no fixed federation) can create or edit global categories.
"""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.enums import RoleName
from app.models.tournament import EventCategory
from app.models.user import User
from app.schemas.tournament import EventCategoryCreate, EventCategoryUpdate
from app.services.errors import ForbiddenError, NotFoundError


def list_categories(
    db: Session, *, tenant_id: uuid.UUID | None, active_only: bool = True
) -> list[EventCategory]:
    stmt = select(EventCategory).where(EventCategory.deleted_at.is_(None))
    if tenant_id is not None:
        stmt = stmt.where(
            or_(EventCategory.federation_id.is_(None), EventCategory.federation_id == tenant_id)
        )
    if active_only:
        stmt = stmt.where(EventCategory.is_active.is_(True))
    stmt = stmt.order_by(EventCategory.discipline, EventCategory.code)
    return list(db.execute(stmt).scalars().all())


def _get_for_read(
    db: Session, category_id: uuid.UUID, *, tenant_id: uuid.UUID | None
) -> EventCategory:
    stmt = select(EventCategory).where(
        EventCategory.id == category_id, EventCategory.deleted_at.is_(None)
    )
    if tenant_id is not None:
        stmt = stmt.where(
            or_(EventCategory.federation_id.is_(None), EventCategory.federation_id == tenant_id)
        )
    obj = db.execute(stmt).scalar_one_or_none()
    if obj is None:
        raise NotFoundError("Event category not found")
    return obj


def get_category(
    db: Session, category_id: uuid.UUID, *, tenant_id: uuid.UUID | None
) -> EventCategory:
    return _get_for_read(db, category_id, tenant_id=tenant_id)


def create_category(db: Session, data: EventCategoryCreate, *, user: User) -> EventCategory:
    if user.federation_id is not None:
        # Tenant-bound users always create within their own federation.
        federation_id: uuid.UUID | None = user.federation_id
    else:
        # Platform super admins choose: None = global default, or on behalf of a federation.
        federation_id = data.federation_id

    obj = EventCategory(
        federation_id=federation_id,
        code=data.code,
        name=data.name,
        discipline=data.discipline,
        gender_scope=data.gender_scope,
        age_min=data.age_min,
        age_max=data.age_max,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def _get_for_write(db: Session, category_id: uuid.UUID, *, user: User) -> EventCategory:
    obj = db.execute(
        select(EventCategory).where(
            EventCategory.id == category_id, EventCategory.deleted_at.is_(None)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NotFoundError("Event category not found")
    is_super = user.is_superuser or RoleName.super_admin.value in user.role_names
    if obj.federation_id is None and not is_super:
        raise ForbiddenError("Only a platform super admin can modify a global category")
    if (
        obj.federation_id is not None
        and user.federation_id is not None
        and obj.federation_id != user.federation_id
    ):
        raise NotFoundError("Event category not found")
    return obj


def update_category(
    db: Session, category_id: uuid.UUID, data: EventCategoryUpdate, *, user: User
) -> EventCategory:
    obj = _get_for_write(db, category_id, user=user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_category(db: Session, category_id: uuid.UUID, *, user: User) -> None:
    from datetime import UTC, datetime

    obj = _get_for_write(db, category_id, user=user)
    obj.deleted_at = datetime.now(UTC)
    db.commit()
