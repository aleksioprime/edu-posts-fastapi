import argparse
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy import or_, select

from src.core.database import async_session_maker
from src.models.post import Post
from src.models.user import User


async def seed_database(
    users_count: int,
    posts_per_user: int,
    password: str,
    session_factory=async_session_maker,
) -> tuple[int, int]:
    """Идемпотентно создаёт demo-пользователей и их публикации."""
    created_users = 0
    created_posts = 0

    async with session_factory() as session:
        for user_number in range(1, users_count + 1):
            username = f"demo{user_number}"
            email = f"demo{user_number}@example.com"
            user = await session.scalar(
                select(User).where(or_(User.username == username, User.email == email))
            )

            if user is None:
                user = User(username=username, email=email, hashed_password="")
                user.set_password(password)
                session.add(user)
                await session.flush()
                created_users += 1
            elif user.username != username or user.email != email:
                raise RuntimeError(
                    f"Нельзя создать {username}: его логин или email занят другим пользователем"
                )
            else:
                # Повторный запуск оставляет данные идемпотентными, но синхронизирует
                # переданный demo-пароль, чтобы напечатанные реквизиты всегда работали.
                user.set_password(password)

            for post_number in range(1, posts_per_user + 1):
                title = f"Тестовый пост {user_number}.{post_number}"
                exists = await session.scalar(
                    select(Post.id).where(Post.author_id == user.id, Post.title == title)
                )
                if exists is not None:
                    continue

                session.add(
                    Post(
                        title=title,
                        content=(
                            f"Тестовая публикация №{post_number} пользователя {username}. "
                            "Эти данные созданы скриптом seed_database.py."
                        ),
                        author_id=user.id,
                    )
                )
                created_posts += 1

        await session.commit()

    return created_users, created_posts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Заполняет базу тестовыми пользователями и постами.")
    parser.add_argument("--users", type=int, default=3, help="Количество demo-пользователей.")
    parser.add_argument(
        "--posts-per-user",
        type=int,
        default=3,
        help="Количество постов каждого пользователя.",
    )
    parser.add_argument("--password", required=True, help="Общий пароль demo-пользователей.")
    args = parser.parse_args()

    if not 1 <= args.users <= 20:
        parser.error("--users должен быть от 1 до 20")
    if not 0 <= args.posts_per_user <= 50:
        parser.error("--posts-per-user должен быть от 0 до 50")
    if len(args.password) < 8:
        parser.error("--password должен содержать не менее 8 символов")

    users, posts = asyncio.run(
        seed_database(args.users, args.posts_per_user, args.password)
    )
    print(f"Тестовые данные готовы: создано пользователей — {users}, постов — {posts}")
    print(f"Логины: demo1 … demo{args.users}; общий пароль передан через --password")
