"""Проверка доступа суперпользователей к административной панели."""

from uuid import UUID

from sqlalchemy import or_, select
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from src.core.database import async_session_maker
from src.models.user import User


class AdminAuth(AuthenticationBackend):
    """Управляет сессией аутентификации администратора."""

    async def login(self, request: Request) -> bool:
        """Проверяет учётные данные и открывает административную сессию."""

        form = await request.form()
        login = str(form.get("username", "")).strip()
        password = str(form.get("password", ""))
        async with async_session_maker() as session:
            user = await session.scalar(
                select(User).where(or_(User.username == login, User.email == login))
            )
        if user is None or not user.is_active or not user.is_superuser or not user.check_password(password):
            return False
        request.session.update({"admin_user_id": str(user.id)})
        return True

    async def logout(self, request: Request) -> bool:
        """Завершает административную сессию."""

        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        """Проверяет активного суперпользователя в текущей сессии."""

        user_id = request.session.get("admin_user_id")
        if not user_id:
            return False
        async with async_session_maker() as session:
            try:
                user = await session.get(User, UUID(user_id))
            except (TypeError, ValueError):
                return False
        return bool(user and user.is_active and user.is_superuser)
