"""Roles and the user_roles association (RBAC)."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import GUID, JSONType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# M:N association between users and roles.
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", GUID(), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", GUID(), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255))
    permissions: Mapped[list | None] = mapped_column(JSONType(), default=list)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Role {self.name}>"
