"""Business logic for state associations."""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.org import StateAssociation
from app.schemas.state import StateCreate, StateUpdate
from app.services.crud import paginate, resolve_write_federation, scope_to_tenant
from app.services.errors import ConflictError, NotFoundError


def list_states(
    db: Session,
    *,
    tenant_id: uuid.UUID | None,
    q: str | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[StateAssociation], int]:
    stmt = select(StateAssociation).where(StateAssociation.deleted_at.is_(None))
    stmt = scope_to_tenant(stmt, StateAssociation, tenant_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(StateAssociation.name.ilike(like), StateAssociation.code.ilike(like))
        )
    stmt = stmt.order_by(StateAssociation.name)
    return paginate(db, stmt, page, size)


def get_state(
    db: Session, state_id: uuid.UUID, *, tenant_id: uuid.UUID | None
) -> StateAssociation:
    stmt = select(StateAssociation).where(
        StateAssociation.id == state_id, StateAssociation.deleted_at.is_(None)
    )
    stmt = scope_to_tenant(stmt, StateAssociation, tenant_id)
    obj = db.execute(stmt).scalar_one_or_none()
    if obj is None:
        raise NotFoundError("State association not found")
    return obj


def create_state(
    db: Session, data: StateCreate, *, user_federation_id: uuid.UUID | None
) -> StateAssociation:
    federation_id = resolve_write_federation(user_federation_id, data.federation_id)
    obj = StateAssociation(
        federation_id=federation_id,
        name=data.name,
        code=data.code,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("A state with this name already exists") from exc
    db.refresh(obj)
    return obj


def update_state(
    db: Session,
    state_id: uuid.UUID,
    data: StateUpdate,
    *,
    tenant_id: uuid.UUID | None,
) -> StateAssociation:
    obj = get_state(db, state_id, tenant_id=tenant_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("A state with this name already exists") from exc
    db.refresh(obj)
    return obj


def delete_state(
    db: Session, state_id: uuid.UUID, *, tenant_id: uuid.UUID | None
) -> None:
    from datetime import UTC, datetime

    obj = get_state(db, state_id, tenant_id=tenant_id)
    obj.deleted_at = datetime.now(UTC)
    db.commit()
