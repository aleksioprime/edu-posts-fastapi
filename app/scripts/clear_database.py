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


async def clear_database(session_factory=async_session_maker) -> tuple[int, int]:
    """Удаляет прикладные данные, сохраняя таблицы и версию Alembic."""
    async with session_factory() as session:
        post_count = await session.scalar(select(func.count()).select_from(Post)) or 0
        user_count = await session.scalar(select(func.count()).select_from(User)) or 0

        await session.execute(delete(Post))
        await session.execute(delete(User))
        await session.commit()

    return user_count, post_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Удаляет всех пользователей и посты, не меняя структуру базы данных."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Подтвердить необратимое удаление данных.",
    )
    args = parser.parse_args()
    if not args.yes:
        parser.error("Очистка отменена. Для подтверждения передайте --yes")

    users, posts = asyncio.run(clear_database())
    print(f"База очищена: удалено пользователей — {users}, постов — {posts}")

