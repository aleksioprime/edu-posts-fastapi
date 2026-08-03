"""Схемы создания, изменения и чтения постов."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.user import UserPublic


class PostCreate(BaseModel):
    """Данные для создания поста."""

    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)


class PostUpdate(BaseModel):
    """Необязательные поля для изменения поста."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)


class PostRead(BaseModel):
    """Публичное представление поста."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    content: str
    image_url: str | None
    author: UserPublic
    created_at: datetime
    updated_at: datetime


class PostList(BaseModel):
    """Страница постов с параметрами пагинации."""

    items: list[PostRead]
    total: int
    limit: int
    offset: int
