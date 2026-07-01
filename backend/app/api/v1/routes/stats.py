"""Dashboard statistics endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_tenant_id
from app.models.user import User
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


class OverviewStats(BaseModel):
    total_players: int
    active_players: int
    total_clubs: int
    total_states: int
    total_tournaments: int
    active_tournaments: int


@router.get("/overview", response_model=OverviewStats)
def overview(
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    return stats_service.overview(db, tenant_id)
