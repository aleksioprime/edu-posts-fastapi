"""Команда создания суперпользователя."""

import argparse
import asyncio
import sys
from pathlib import Path

# Позволяет одинаково запускать скрипт как модуль и как файл из корня приложения.
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy import or_, select

from src.core.database import async_session_maker
from src.models.user import User


async def create_superuser(
    username: str,
    email: str,
    password: str,
    session_factory=async_session_maker,
) -> None:
    """Создаёт суперпользователя с уникальными логином и email."""

    async with session_factory() as session:
        exists = await session.scalar(
            select(User).where(or_(User.username == username, User.email == email.lower()))
        )
        if exists:
            raise SystemExit("Пользователь с таким логином или email уже существует")
        user = User(username=username, email=email.lower(), hashed_password="", is_superuser=True)
        user.set_password(password)
        session.add(user)
        await session.commit()
    print(f"Суперпользователь {username} создан")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("email")
    parser.add_argument("password")
    args = parser.parse_args()
    asyncio.run(create_superuser(args.username, args.email, args.password))
