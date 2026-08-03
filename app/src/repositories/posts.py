"""Запросы к таблице постов."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.post import Post


class PostRepository:
    """Инкапсулирует операции чтения и записи постов."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(
        self,
        limit: int,
        offset: int,
        author_id: UUID | None = None,
    ) -> tuple[list[Post], int]:
        """Возвращает страницу постов и их общее количество."""

        query = select(Post).options(selectinload(Post.author))
        count_query = select(func.count()).select_from(Post)

        if author_id is not None:
            query = query.where(Post.author_id == author_id)
            count_query = count_query.where(Post.author_id == author_id)

        query = query.order_by(Post.created_at.desc()).limit(limit).offset(offset)
        posts = list((await self.session.scalars(query)).all())
        total = await self.session.scalar(count_query)
        return posts, total or 0

    async def get_by_id(self, post_id: UUID) -> Post | None:
        """Находит пост по идентификатору вместе с автором."""

        query = select(Post).options(selectinload(Post.author)).where(Post.id == post_id)
        return (await self.session.scalars(query)).one_or_none()

    async def create(self, post: Post) -> Post:
        """Добавляет новый пост в текущую сессию."""

        self.session.add(post)
        await self.session.flush()
        await self.session.refresh(post, attribute_names=["author"])
        return post

    async def delete(self, post: Post) -> None:
        """Помечает пост для удаления в текущей сессии."""

        await self.session.delete(post)
