"""Схемы ответов авторизации."""

from pydantic import BaseModel


class Token(BaseModel):
    """JWT-токен доступа."""

    access_token: str
    token_type: str = "bearer"
