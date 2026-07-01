"""Player endpoints, including CSV/Excel import and export."""

from __future__ import annotations

import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_active_user,
    get_tenant_id,
    require_permission,
)
from app.core.rbac import Permission
from app.models.enums import Gender, PlayerStatus
from app.models.player import Player
from app.models.user import User
from app.schemas.common import Message, Page
from app.schemas.player import (
    ImportResult,
    PlayerCreate,
    PlayerRead,
    PlayerReadDetail,
    PlayerUpdate,
)
from app.services import player_io, player_service
from app.services.audit_service import record_audit
from app.services.crud import resolve_write_federation

router = APIRouter(prefix="/players", tags=["players"])


def _read(player: Player) -> PlayerRead:
    return PlayerRead.model_validate(player).model_copy(update=player_service.enrich(player))


def _detail(db: Session, player: Player) -> PlayerReadDetail:
    return PlayerReadDetail.model_validate(player).model_copy(
        update=player_service.player_detail(db, player)
    )


@router.get("", response_model=Page[PlayerRead])
def list_players(
    q: str | None = Query(default=None),
    status_filter: PlayerStatus | None = Query(default=None, alias="status"),
    gender: Gender | None = Query(default=None),
    club_id: uuid.UUID | None = Query(default=None),
    state_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    items, total = player_service.list_players(
        db,
        tenant_id=tenant_id,
        q=q,
        status=status_filter,
        gender=gender,
        club_id=club_id,
        state_id=state_id,
        page=page,
        size=size,
    )
    return Page.create(items=[_read(p) for p in items], total=total, page=page, size=size)


@router.get("/export")
def export_players(
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(require_permission(Permission.EXPORT_REPORTS)),
):
    # Export the full (unpaginated) set.
    players = player_service.list_all_players(db, tenant_id=tenant_id)
    if format == "xlsx":
        content = player_io.export_xlsx(db, players)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "players.xlsx"
    else:
        content = player_io.export_csv(db, players)
        media = "text/csv"
        filename = "players.csv"
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=ImportResult)
def import_players(
    request: Request,
    file: UploadFile = File(...),
    federation_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.IMPORT_PLAYERS)),
):
    fed_id = resolve_write_federation(user.federation_id, federation_id)
    content = file.file.read()
    result = player_io.import_players(db, content, file.filename or "", federation_id=fed_id)
    record_audit(
        db,
        action="player.import",
        actor_user_id=user.id,
        federation_id=fed_id,
        entity_type="player",
        after={
            "created": result.created,
            "updated": result.updated,
            "skipped": result.skipped,
        },
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return result


@router.get("/{player_id}", response_model=PlayerReadDetail)
def get_player(
    player_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID | None = Depends(get_tenant_id),
    _: User = Depends(get_current_active_user),
):
    player = player_service.get_player(db, player_id, tenant_id=tenant_id)
    return _detail(db, player)


@router.post("", response_model=PlayerRead, status_code=status.HTTP_201_CREATED)
def create_player(
    request: Request,
    body: PlayerCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_PLAYERS)),
):
    obj = player_service.create_player(db, body, user_federation_id=user.federation_id)
    record_audit(
        db,
        action="player.create",
        actor_user_id=user.id,
        federation_id=obj.federation_id,
        entity_type="player",
        entity_id=str(obj.id),
        after={"code": obj.federation_player_code, "name": obj.full_name},
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _read(obj)


@router.put("/{player_id}", response_model=PlayerRead)
def update_player(
    player_id: uuid.UUID,
    body: PlayerUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_PLAYERS)),
):
    obj = player_service.update_player(db, player_id, body, tenant_id=user.federation_id)
    record_audit(
        db,
        action="player.update",
        actor_user_id=user.id,
        federation_id=obj.federation_id,
        entity_type="player",
        entity_id=str(obj.id),
        after=body.model_dump(exclude_unset=True, mode="json"),
    )
    return _read(obj)


@router.delete("/{player_id}", response_model=Message)
def delete_player(
    player_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_PLAYERS)),
):
    player_service.delete_player(db, player_id, tenant_id=user.federation_id)
    record_audit(
        db,
        action="player.delete",
        actor_user_id=user.id,
        federation_id=user.federation_id,
        entity_type="player",
        entity_id=str(player_id),
    )
    return Message(detail="Player deleted")
