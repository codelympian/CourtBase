"""Ranking rule endpoints (configurable points tables)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_tenant_id, require_permission
from app.core.rbac import Permission
from app.models.enums import TournamentLevel
from app.models.user import User
from app.schemas.common import Message
from app.schemas.ranking import (
    RankingPointRead,
    RankingRuleCreate,
    RankingRuleRead,
    RankingRuleUpdate,
)
from app.services import ranking_rule_service
from app.services.audit_service import record_audit

router = APIRouter(prefix="/ranking-rules", tags=["ranking-rules"])


def _read(db: Session, rule) -> RankingRuleRead:
    points = [
        RankingPointRead.model_validate(p)
        for p in ranking_rule_service.as_read_dict(db, rule)["points"]
    ]
    return RankingRuleRead(
        id=rule.id,
        federation_id=rule.federation_id,
        name=rule.name,
        level=rule.level,
        category_id=rule.category_id,
        is_active=rule.is_active,
        points=points,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.get("", response_model=list[RankingRuleRead])
def list_rules(
    level: TournamentLevel | None = Query(default=None),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    rules = ranking_rule_service.list_rules(db, tenant_id=tenant_id, level=level)
    return [_read(db, r) for r in rules]


@router.get("/{rule_id}", response_model=RankingRuleRead)
def get_rule(
    rule_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    return _read(db, ranking_rule_service.get_rule(db, rule_id, tenant_id=tenant_id))


@router.post("", response_model=RankingRuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(
    request: Request,
    body: RankingRuleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_RANKING_RULES)),
):
    rule = ranking_rule_service.create_rule(db, body, user_federation_id=user.federation_id)
    record_audit(
        db,
        action="ranking_rule.create",
        actor_user_id=user.id,
        federation_id=rule.federation_id,
        entity_type="ranking_rule",
        entity_id=str(rule.id),
        after={"name": rule.name, "level": rule.level.value},
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _read(db, rule)


@router.put("/{rule_id}", response_model=RankingRuleRead)
def update_rule(
    rule_id: uuid.UUID,
    body: RankingRuleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_RANKING_RULES)),
):
    rule = ranking_rule_service.update_rule(db, rule_id, body, tenant_id=user.federation_id)
    record_audit(
        db,
        action="ranking_rule.update",
        actor_user_id=user.id,
        federation_id=rule.federation_id,
        entity_type="ranking_rule",
        entity_id=str(rule.id),
    )
    return _read(db, rule)


@router.delete("/{rule_id}", response_model=Message)
def delete_rule(
    rule_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_RANKING_RULES)),
):
    ranking_rule_service.delete_rule(db, rule_id, tenant_id=user.federation_id)
    record_audit(
        db,
        action="ranking_rule.delete",
        actor_user_id=user.id,
        federation_id=user.federation_id,
        entity_type="ranking_rule",
        entity_id=str(rule_id),
    )
    return Message(detail="Ranking rule deleted")
