"""Registration detail endpoints (update seed/status, withdraw)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_tenant_id, require_permission
from app.core.rbac import Permission
from app.models.user import User
from app.schemas.common import Message
from app.schemas.registration import RegistrationRead, RegistrationReadDetail, RegistrationUpdate
from app.services import registration_service
from app.services.audit_service import record_audit

router = APIRouter(prefix="/registrations", tags=["registrations"])


def _detail(db: Session, reg) -> RegistrationReadDetail:
    base = RegistrationRead.model_validate(reg).model_dump()
    return RegistrationReadDetail(**base, **registration_service.registration_detail(db, reg))


@router.get("/{registration_id}", response_model=RegistrationReadDetail)
def get_registration(
    registration_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    reg = registration_service.get_registration(db, registration_id, tenant_id=tenant_id)
    return _detail(db, reg)


@router.put("/{registration_id}", response_model=RegistrationReadDetail)
def update_registration(
    registration_id: uuid.UUID,
    body: RegistrationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_TOURNAMENTS)),
):
    reg = registration_service.update_registration(
        db, registration_id, body, tenant_id=user.federation_id
    )
    record_audit(
        db,
        action="registration.update",
        actor_user_id=user.id,
        federation_id=reg.federation_id,
        entity_type="registration",
        entity_id=str(reg.id),
        after=body.model_dump(exclude_unset=True, mode="json"),
    )
    return _detail(db, reg)


@router.delete("/{registration_id}", response_model=Message)
def delete_registration(
    registration_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_TOURNAMENTS)),
):
    registration_service.delete_registration(db, registration_id, tenant_id=user.federation_id)
    record_audit(
        db,
        action="registration.withdraw",
        actor_user_id=user.id,
        federation_id=user.federation_id,
        entity_type="registration",
        entity_id=str(registration_id),
    )
    return Message(detail="Registration withdrawn")
