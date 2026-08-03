from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.post import Post


class PostRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, limit: int, offset: int) -> tuple[list[Post], int]:
        query = (
            select(Post)
            .options(selectinload(Post.author))
            .order_by(Post.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        posts = list((await self.session.scalars(query)).all())
        total = await self.session.scalar(select(func.count()).select_from(Post))
        return posts, total or 0

    async def get_by_id(self, post_id: UUID) -> Post | None:
        query = select(Post).options(selectinload(Post.author)).where(Post.id == post_id)
        return (await self.session.scalars(query)).one_or_none()

    async def create(self, post: Post) -> Post:
        self.session.add(post)
        await self.session.flush()
        await self.session.refresh(post, attribute_names=["author"])
        return post

    async def delete(self, post: Post) -> None:
        await self.session.delete(post)

