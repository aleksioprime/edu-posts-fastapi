"""Фабрики зависимостей FastAPI."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.repositories.uow import UnitOfWork
from src.services.auth import AuthService
from src.services.image_storage import PostImageStorage
from src.services.posts import PostService


def get_uow(session: AsyncSession = Depends(get_session)) -> UnitOfWork:
    """Создаёт единицу работы для текущей сессии базы данных."""

    return UnitOfWork(session)


def get_auth_service(uow: UnitOfWork = Depends(get_uow)) -> AuthService:
    """Создаёт сервис регистрации и авторизации."""

    return AuthService(uow)


def get_image_storage() -> PostImageStorage:
    """Создаёт хранилище изображений постов."""

    return PostImageStorage()


def get_post_service(
    uow: UnitOfWork = Depends(get_uow),
    image_storage: PostImageStorage = Depends(get_image_storage),
) -> PostService:
    """Создаёт сервис управления постами."""

    return PostService(uow, image_storage)
