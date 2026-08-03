"""Запросы к таблице пользователей."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User


class UserRepository:
    """Инкапсулирует операции чтения и записи пользователей."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Находит пользователя по идентификатору."""

        return await self.session.get(User, user_id)

    async def get_by_login(self, login: str) -> User | None:
        """Находит пользователя по имени или email."""

        result = await self.session.execute(
            select(User).where(or_(User.username == login, User.email == login))
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Добавляет нового пользователя в текущую сессию."""

        self.session.add(user)
        await self.session.flush()
        return user
