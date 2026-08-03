from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.repositories.uow import UnitOfWork
from src.services.auth import AuthService
from src.services.posts import PostService


def get_uow(session: AsyncSession = Depends(get_session)) -> UnitOfWork:
    return UnitOfWork(session)


def get_auth_service(uow: UnitOfWork = Depends(get_uow)) -> AuthService:
    return AuthService(uow)


def get_post_service(uow: UnitOfWork = Depends(get_uow)) -> PostService:
    return PostService(uow)

