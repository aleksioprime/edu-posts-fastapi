"""Схемы регистрации и чтения пользователей."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Данные для регистрации пользователя."""

    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserPublic(BaseModel):
    """Публичные данные автора поста."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str


class UserMe(UserPublic):
    """Профиль текущего пользователя."""

    email: EmailStr
    is_active: bool
    created_at: datetime
