"""Match detail and score-entry endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_tenant_id, require_permission
from app.core.rbac import Permission
from app.models.user import User
from app.schemas.match import MatchRead, MatchReadDetail, MatchScoreInput
from app.services import match_service
from app.services.audit_service import record_audit

router = APIRouter(prefix="/matches", tags=["matches"])


def _detail(db: Session, match) -> MatchReadDetail:
    base = MatchRead.model_validate(match).model_dump()
    return MatchReadDetail(**base, **match_service.match_detail(db, match))


@router.get("/{match_id}", response_model=MatchReadDetail)
def get_match(
    match_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    match = match_service.get_match(db, match_id, tenant_id=tenant_id)
    return _detail(db, match)


@router.post("/{match_id}/score", response_model=MatchReadDetail)
def record_score(
    match_id: uuid.UUID,
    body: MatchScoreInput,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.ENTER_SCORES)),
):
    match = match_service.record_score(db, match_id, body, tenant_id=user.federation_id)
    record_audit(
        db,
        action="match.score",
        actor_user_id=user.id,
        federation_id=match.federation_id,
        entity_type="match",
        entity_id=str(match.id),
        after={
            "score": match.score,
            "winner_id": str(match.winner_id),
            "status": match.status.value,
        },
    )
    return _detail(db, match)
