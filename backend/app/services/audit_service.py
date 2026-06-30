"""Helper for writing audit log entries."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record_audit(
    db: Session,
    *,
    action: str,
    actor_user_id: uuid.UUID | None = None,
    federation_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    commit: bool = True,
) -> AuditLog:
    """Persist an audit entry. Caller controls commit (default True)."""
    entry = AuditLog(
        action=action,
        actor_user_id=actor_user_id,
        federation_id=federation_id,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        ip=ip,
        user_agent=user_agent,
    )
    db.add(entry)
    if commit:
        db.commit()
    return entry
