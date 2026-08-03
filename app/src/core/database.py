"""Настройка асинхронного подключения к базе данных."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings


class Base(DeclarativeBase):
    """Базовый класс ORM-моделей приложения."""

    pass


engine = create_async_engine(settings.database_url, echo=settings.show_sql)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Предоставляет сессию базы данных на время запроса."""

    async with async_session_maker() as session:
        yield session
