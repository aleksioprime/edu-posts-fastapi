from fastapi import FastAPI
from sqladmin import Admin

from src.admin.auth import AdminAuth
from src.admin.views import PostAdmin, UserAdmin
from src.core.config import settings
from src.core.database import async_session_maker


def setup_admin(app: FastAPI) -> Admin:
    admin = Admin(
        app,
        session_maker=async_session_maker,
        base_url="/admin",
        title="Edu Posts — администрирование",
        authentication_backend=AdminAuth(secret_key=settings.admin_session_secret),
    )
    admin.add_view(UserAdmin)
    admin.add_view(PostAdmin)
    return admin

