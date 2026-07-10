"""CRUD for ranking rules and their points tables."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import TournamentLevel
from app.models.ranking import RankingPoint, RankingRule
from app.schemas.ranking import RankingPointInput, RankingRuleCreate, RankingRuleUpdate
from app.services.crud import resolve_write_federation, scope_to_tenant
from app.services.errors import NotFoundError, ValidationError


def _load_points(db: Session, rule_id: uuid.UUID) -> list[RankingPoint]:
    return list(
        db.execute(
            select(RankingPoint).where(RankingPoint.rule_id == rule_id).order_by(
                RankingPoint.points.desc()
            )
        )
        .scalars()
        .all()
    )


def as_read_dict(db: Session, rule: RankingRule) -> dict:
    """Extra fields for RankingRuleRead (the points list)."""
    return {"points": _load_points(db, rule.id)}


def list_rules(
    db: Session, *, tenant_id: uuid.UUID | None, level: TournamentLevel | None = None
) -> list[RankingRule]:
    stmt = select(RankingRule).where(RankingRule.deleted_at.is_(None))
    stmt = scope_to_tenant(stmt, RankingRule, tenant_id)
    if level:
        stmt = stmt.where(RankingRule.level == level)
    stmt = stmt.order_by(RankingRule.level, RankingRule.name)
    return list(db.execute(stmt).scalars().all())


def get_rule(db: Session, rule_id: uuid.UUID, *, tenant_id: uuid.UUID | None) -> RankingRule:
    stmt = select(RankingRule).where(
        RankingRule.id == rule_id, RankingRule.deleted_at.is_(None)
    )
    stmt = scope_to_tenant(stmt, RankingRule, tenant_id)
    obj = db.execute(stmt).scalar_one_or_none()
    if obj is None:
        raise NotFoundError("Ranking rule not found")
    return obj


def _validate_points(points: list[RankingPointInput]) -> None:
    keys = [p.result_key for p in points]
    if len(keys) != len(set(keys)):
        raise ValidationError("Duplicate result_key in points table")


def _replace_points(
    db: Session, rule: RankingRule, points: list[RankingPointInput]
) -> None:
    db.execute(
        RankingPoint.__table__.delete().where(RankingPoint.rule_id == rule.id)
    )
    for p in points:
        db.add(
            RankingPoint(
                federation_id=rule.federation_id,
                rule_id=rule.id,
                result_key=p.result_key,
                points=p.points,
            )
        )


def create_rule(
    db: Session, data: RankingRuleCreate, *, user_federation_id: uuid.UUID | None
) -> RankingRule:
    federation_id = resolve_write_federation(user_federation_id, data.federation_id)
    _validate_points(data.points)
    rule = RankingRule(
        federation_id=federation_id,
        name=data.name,
        level=data.level,
        category_id=data.category_id,
    )
    db.add(rule)
    db.flush()
    _replace_points(db, rule, data.points)
    db.commit()
    db.refresh(rule)
    return rule


def update_rule(
    db: Session, rule_id: uuid.UUID, data: RankingRuleUpdate, *, tenant_id: uuid.UUID | None
) -> RankingRule:
    rule = get_rule(db, rule_id, tenant_id=tenant_id)
    payload = data.model_dump(exclude_unset=True)
    points = payload.pop("points", None)
    for field, value in payload.items():
        setattr(rule, field, value)
    if points is not None:
        _validate_points(data.points or [])
        _replace_points(db, rule, data.points or [])
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule_id: uuid.UUID, *, tenant_id: uuid.UUID | None) -> None:
    rule = get_rule(db, rule_id, tenant_id=tenant_id)
    rule.deleted_at = datetime.now(UTC)
    db.commit()


def resolve_rule_for_event(
    db: Session,
    *,
    federation_id: uuid.UUID,
    level: TournamentLevel,
    category_id: uuid.UUID,
) -> RankingRule | None:
    """Find the active rule for a tournament level, preferring a category-specific
    rule over a level-wide (category-less) one."""
    rules = list(
        db.execute(
            select(RankingRule).where(
                RankingRule.federation_id == federation_id,
                RankingRule.level == level,
                RankingRule.is_active.is_(True),
                RankingRule.deleted_at.is_(None),
            )
        )
        .scalars()
        .all()
    )
    specific = [r for r in rules if r.category_id == category_id]
    if specific:
        return specific[0]
    generic = [r for r in rules if r.category_id is None]
    return generic[0] if generic else None


def points_map(db: Session, rule: RankingRule) -> dict[str, int]:
    return {p.result_key: p.points for p in _load_points(db, rule.id)}
