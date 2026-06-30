"""Shared schema helpers: base config and pagination envelope."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base for response models read from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    detail: str


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, items: list[T], total: int, page: int, size: int) -> Page[T]:
        pages = (total + size - 1) // size if size else 0
        return cls(items=items, total=total, page=page, size=size, pages=pages)
