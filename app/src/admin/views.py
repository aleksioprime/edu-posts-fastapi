from sqladmin import ModelView

from src.models.post import Post
from src.models.user import User


class UserAdmin(ModelView, model=User):
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-users"
    column_list = [User.id, User.username, User.email, User.is_active, User.is_superuser, User.created_at]
    column_searchable_list = [User.username, User.email]
    column_sortable_list = [User.username, User.email, User.created_at]
    form_excluded_columns = [User.posts, User.hashed_password, User.created_at]
    can_create = False


class PostAdmin(ModelView, model=Post):
    name = "Пост"
    name_plural = "Посты"
    icon = "fa-solid fa-newspaper"
    column_list = [Post.id, Post.title, Post.author, Post.created_at, Post.updated_at]
    column_searchable_list = [Post.title, Post.content]
    column_sortable_list = [Post.title, Post.created_at, Post.updated_at]
    form_excluded_columns = [Post.created_at, Post.updated_at]
