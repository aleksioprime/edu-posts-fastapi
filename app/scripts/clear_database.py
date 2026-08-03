"""Команда удаления прикладных данных и изображений."""

import argparse
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy import delete, func, select

from src.core.database import async_session_maker
from src.models.post import Post
from src.models.user import User
from src.services.image_storage import PostImageStorage


async def clear_database(
    session_factory=async_session_maker,
    image_storage: PostImageStorage | None = None,
) -> tuple[int, int, int]:
    """Удаляет посты и обычных пользователей, сохраняя суперпользователей."""

    async with session_factory() as session:
        post_count = await session.scalar(select(func.count()).select_from(Post)) or 0
        user_count = await session.scalar(
            select(func.count()).select_from(User).where(User.is_superuser.is_(False))
        ) or 0

        await session.execute(delete(Post))
        await session.execute(delete(User).where(User.is_superuser.is_(False)))
        await session.commit()

    deleted_images = (image_storage or PostImageStorage()).clear()
    return user_count, post_count, deleted_images


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Удаляет посты и обычных пользователей, сохраняя суперпользователей "
            "и структуру базы данных."
        )
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Подтвердить необратимое удаление данных.",
    )
    args = parser.parse_args()
    if not args.yes:
        parser.error("Очистка отменена. Для подтверждения передайте --yes")

    users, posts, images = asyncio.run(clear_database())
    print(
        "База очищена: "
        f"удалено обычных пользователей — {users}, постов — {posts}, "
        f"изображений — {images}; суперпользователи сохранены"
    )
