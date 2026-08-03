from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.posts import PostRepository
from src.repositories.users import UserRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.posts = PostRepository(session)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

