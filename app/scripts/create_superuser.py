import argparse
import asyncio

from sqlalchemy import or_, select

from src.core.database import async_session_maker
from src.models.user import User


async def create_superuser(username: str, email: str, password: str) -> None:
    async with async_session_maker() as session:
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

