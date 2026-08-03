from sqlalchemy import func, select

from scripts.clear_database import clear_database
from scripts.seed_database import seed_database
from src.models.post import Post
from src.models.user import User


async def test_seed_is_idempotent_and_clear_removes_data(test_session_maker):
    created = await seed_database(
        users_count=2,
        posts_per_user=2,
        password="demo-password",
        session_factory=test_session_maker,
    )
    assert created == (2, 4)

    repeated = await seed_database(
        users_count=2,
        posts_per_user=2,
        password="demo-password",
        session_factory=test_session_maker,
    )
    assert repeated == (0, 0)

    async with test_session_maker() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 2
        assert await session.scalar(select(func.count()).select_from(Post)) == 4

    assert await clear_database(session_factory=test_session_maker) == (2, 4, 0)

    async with test_session_maker() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 0
        assert await session.scalar(select(func.count()).select_from(Post)) == 0
