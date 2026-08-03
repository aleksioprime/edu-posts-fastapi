from uuid import UUID

from fastapi import HTTPException

from src.models.post import Post
from src.models.user import User
from src.repositories.uow import UnitOfWork
from src.schemas.post import PostCreate, PostList, PostRead, PostUpdate


class PostService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_all(self, limit: int, offset: int) -> PostList:
        posts, total = await self.uow.posts.get_all(limit, offset)
        return PostList(items=[PostRead.model_validate(post) for post in posts], total=total, limit=limit, offset=offset)

    async def get_by_id(self, post_id: UUID) -> Post:
        post = await self.uow.posts.get_by_id(post_id)
        if post is None:
            raise HTTPException(status_code=404, detail="Пост не найден")
        return post

    async def create(self, data: PostCreate, user: User) -> Post:
        post = Post(**data.model_dump(), author_id=user.id)
        await self.uow.posts.create(post)
        await self.uow.commit()
        return post

    async def update(self, post_id: UUID, data: PostUpdate, user: User) -> Post:
        post = await self.get_by_id(post_id)
        self._ensure_owner(post, user)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            raise HTTPException(status_code=422, detail="Не переданы поля для обновления")
        for field, value in changes.items():
            setattr(post, field, value)
        await self.uow.commit()
        # updated_at вычисляется базой данных; явно обновляем объект до сериализации.
        await self.uow.session.refresh(post)
        await self.uow.session.refresh(post, attribute_names=["author"])
        return post

    async def delete(self, post_id: UUID, user: User) -> None:
        post = await self.get_by_id(post_id)
        self._ensure_owner(post, user)
        await self.uow.posts.delete(post)
        await self.uow.commit()

    @staticmethod
    def _ensure_owner(post: Post, user: User) -> None:
        if post.author_id != user.id and not user.is_superuser:
            raise HTTPException(status_code=403, detail="Можно изменять только свои посты")
