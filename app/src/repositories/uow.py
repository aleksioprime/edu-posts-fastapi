"""Единица работы для согласованных операций с репозиториями."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.posts import PostRepository
from src.repositories.users import UserRepository


class UnitOfWork:
    """Объединяет репозитории и управление транзакцией."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.posts = PostRepository(session)

    async def commit(self) -> None:
        """Фиксирует текущую транзакцию."""

        await self.session.commit()

    async def rollback(self) -> None:
        """Откатывает текущую транзакцию."""

        await self.session.rollback()
