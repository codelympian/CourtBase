"""Ranking standings, recalculation, publishing, and history."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_tenant_id, require_permission
from app.core.rbac import Permission
from app.models.user import User
from app.schemas.ranking import (
    PublishRequest,
    RankingActionResult,
    RankingHistoryRead,
    RankingRow,
    RecalculateRequest,
)
from app.services import ranking_service
from app.services.audit_service import record_audit

router = APIRouter(prefix="/rankings", tags=["rankings"])


def _resolve_federation(
    tenant_id: uuid.UUID | None, federation_id: uuid.UUID | None
) -> uuid.UUID:
    fed = tenant_id or federation_id
    if fed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="federation_id is required for platform super admins",
        )
    return fed


@router.get("", response_model=list[RankingRow])
def list_rankings(
    category_id: uuid.UUID = Query(...),
    published: bool = Query(default=False),
    as_of: date | None = Query(default=None),
    federation_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    fed = _resolve_federation(tenant_id, federation_id)
    return ranking_service.list_rankings(
        db,
        federation_id=fed,
        category_id=category_id,
        published_only=published,
        as_of=as_of,
    )


@router.get("/history", response_model=list[RankingHistoryRead])
def ranking_history(
    player_id: uuid.UUID = Query(...),
    category_id: uuid.UUID | None = Query(default=None),
    federation_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    fed = _resolve_federation(tenant_id, federation_id)
    return ranking_service.list_history(
        db, federation_id=fed, player_id=player_id, category_id=category_id
    )


@router.post("/recalculate", response_model=RankingActionResult)
def recalculate(
    body: RecalculateRequest,
    federation_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.APPROVE_RANKINGS)),
):
    fed = _resolve_federation(user.federation_id, federation_id)
    categories, players, as_of = ranking_service.recalculate(
        db, federation_id=fed, category_id=body.category_id
    )
    record_audit(
        db,
        action="ranking.recalculate",
        actor_user_id=user.id,
        federation_id=fed,
        entity_type="ranking",
        after={"categories": categories, "players": players, "as_of": as_of.isoformat()},
    )
    return RankingActionResult(categories=categories, players=players, as_of=as_of)


@router.post("/publish", response_model=RankingActionResult)
def publish(
    body: PublishRequest,
    federation_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.APPROVE_RANKINGS)),
):
    fed = _resolve_federation(user.federation_id, federation_id)
    if body.category_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="category_id is required to publish",
        )
    count = ranking_service.publish(
        db, federation_id=fed, category_id=body.category_id, as_of=body.as_of
    )
    as_of = body.as_of or date.today()
    record_audit(
        db,
        action="ranking.publish",
        actor_user_id=user.id,
        federation_id=fed,
        entity_type="ranking",
        entity_id=str(body.category_id),
        after={"published_rows": count},
    )
    return RankingActionResult(categories=1, players=count, as_of=as_of)
