"""Сценарии управления постами и их изображениями."""

from uuid import UUID

from fastapi import HTTPException, UploadFile

from src.models.post import Post
from src.models.user import User
from src.repositories.uow import UnitOfWork
from src.schemas.post import PostCreate, PostList, PostRead, PostUpdate
from src.services.image_storage import PostImageStorage


class PostService:
    """Реализует бизнес-правила работы с постами."""

    def __init__(self, uow: UnitOfWork, image_storage: PostImageStorage):
        self.uow = uow
        self.image_storage = image_storage

    async def get_all(self, limit: int, offset: int) -> PostList:
        """Возвращает страницу публичных постов."""

        posts, total = await self.uow.posts.get_all(limit, offset)
        return PostList(items=[PostRead.model_validate(post) for post in posts], total=total, limit=limit, offset=offset)

    async def get_by_id(self, post_id: UUID) -> Post:
        """Возвращает пост или сообщает, что он не найден."""

        post = await self.uow.posts.get_by_id(post_id)
        if post is None:
            raise HTTPException(status_code=404, detail="Пост не найден")
        return post

    async def create(self, data: PostCreate, user: User) -> Post:
        """Создаёт пост от имени текущего пользователя."""

        post = Post(**data.model_dump(), author_id=user.id)
        await self.uow.posts.create(post)
        await self.uow.commit()
        return post

    async def update(self, post_id: UUID, data: PostUpdate, user: User) -> Post:
        """Изменяет доступные поля поста после проверки владельца."""

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
        """Удаляет пост и связанное изображение."""

        post = await self.get_by_id(post_id)
        self._ensure_owner(post, user)
        await self.uow.posts.delete(post)
        await self.uow.commit()
        self.image_storage.delete(post_id)

    async def upload_image(self, post_id: UUID, image: UploadFile, user: User) -> Post:
        """Сохраняет изображение поста после проверки владельца."""

        post = await self.get_by_id(post_id)
        self._ensure_owner(post, user)
        had_image = post.image_url is not None
        image_url = await self.image_storage.save(post_id, image)
        post.image_url = image_url
        try:
            await self.uow.commit()
        except Exception:
            if not had_image:
                self.image_storage.delete(post_id)
            raise
        await self.uow.session.refresh(post)
        await self.uow.session.refresh(post, attribute_names=["author"])
        return post

    async def delete_image(self, post_id: UUID, user: User) -> None:
        """Удаляет изображение поста после проверки владельца."""

        post = await self.get_by_id(post_id)
        self._ensure_owner(post, user)
        post.image_url = None
        await self.uow.commit()
        self.image_storage.delete(post_id)

    @staticmethod
    def _ensure_owner(post: Post, user: User) -> None:
        """Разрешает изменение автору поста или суперпользователю."""

        if post.author_id != user.id and not user.is_superuser:
            raise HTTPException(status_code=403, detail="Можно изменять только свои посты")
