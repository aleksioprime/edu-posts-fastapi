"""Представления пользователей и постов в административной панели."""

from markupsafe import Markup, escape
from sqlalchemy import select
from sqladmin import ModelView

from src.core.database import async_session_maker
from src.models.post import Post
from src.models.user import User
from src.services.image_storage import PostImageStorage


class UserAdmin(ModelView, model=User):
    """Настраивает управление пользователями в административной панели."""

    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-users"
    column_list = [User.id, User.username, User.email, User.is_active, User.is_superuser, User.created_at]
    column_searchable_list = [User.username, User.email]
    column_sortable_list = [User.username, User.email, User.created_at]
    form_excluded_columns = [User.posts, User.hashed_password, User.created_at]
    can_create = False

    async def on_model_delete(self, model: User, request) -> None:
        """Запоминает изображения постов до каскадного удаления пользователя."""

        async with async_session_maker() as session:
            post_ids = await session.scalars(select(Post.id).where(Post.author_id == model.id))
            model._deleted_post_ids = list(post_ids)

    async def after_model_delete(self, model: User, request) -> None:
        """Удаляет изображения постов удалённого пользователя."""

        storage = PostImageStorage()
        for post_id in getattr(model, "_deleted_post_ids", []):
            storage.delete(post_id)


class PostAdmin(ModelView, model=Post):
    """Настраивает управление постами и показ миниатюр изображений."""

    name = "Пост"
    name_plural = "Посты"
    icon = "fa-solid fa-newspaper"
    column_list = [Post.id, Post.title, Post.image_url, Post.author, Post.created_at, Post.updated_at]
    column_searchable_list = [Post.title, Post.content]
    column_sortable_list = [Post.title, Post.created_at, Post.updated_at]
    form_excluded_columns = [Post.image_url, Post.created_at, Post.updated_at]
    column_formatters = {
        Post.image_url: lambda model, _: (
            Markup(
                '<img src="{}" alt="" style="max-width:120px;max-height:80px;object-fit:cover">'
            ).format(escape(model.image_url))
            if model.image_url
            else ""
        )
    }

    async def after_model_delete(self, model: Post, request) -> None:
        """Удаляет файл изображения вместе с постом."""

        PostImageStorage().delete(model.id)
