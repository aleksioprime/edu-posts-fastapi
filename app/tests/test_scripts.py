from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import func, select

from scripts.clear_database import clear_database
from scripts.seed_database import PostTemplate, download_post_templates, seed_database
from src.models.post import Post
from src.models.user import User
from src.services.image_storage import PostImageStorage


def make_test_image(_: str) -> bytes:
    """Создаёт изображение без обращения к внешнему API."""

    content = BytesIO()
    Image.new("RGB", (80, 60), color=(90, 140, 70)).save(content, format="JPEG")
    return content.getvalue()


def make_test_templates() -> list[PostTemplate]:
    """Возвращает предсказуемые тексты без обращения к внешнему API."""

    return [
        PostTemplate(title=f"Заголовок {number}", content=f"Содержимое {number}")
        for number in range(1, 101)
    ]


def test_download_post_templates_validates_and_normalizes_response(monkeypatch):
    """Проверяет преобразование ответа JSONPlaceholder в шаблоны."""

    response = BytesIO(b'[{"title": " first title ", "body": "Post body"}]')
    monkeypatch.setattr(
        "scripts.seed_database.urlopen",
        lambda request, timeout: response,
    )

    assert download_post_templates() == [
        PostTemplate(title="First title", content="Post body")
    ]


async def test_seed_is_idempotent_and_clear_removes_data(test_session_maker, tmp_path):
    """Проверяет тексты, изображения, идемпотентность и очистку seed-данных."""

    storage = PostImageStorage(root=tmp_path)
    created = await seed_database(
        users_count=2,
        posts_per_user=2,
        password="demo-password",
        session_factory=test_session_maker,
        image_storage=storage,
        image_loader=make_test_image,
        text_loader=make_test_templates,
    )
    assert created == (2, 4)

    repeated = await seed_database(
        users_count=2,
        posts_per_user=2,
        password="demo-password",
        session_factory=test_session_maker,
        image_storage=storage,
        image_loader=make_test_image,
        text_loader=make_test_templates,
    )
    assert repeated == (0, 0)

    async with test_session_maker() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 2
        assert await session.scalar(select(func.count()).select_from(Post)) == 4
        assert await session.scalar(
            select(func.count()).select_from(Post).where(Post.image_url.is_not(None))
        ) == 4
        first_post = await session.scalar(select(Post).where(Post.title == "Заголовок 1"))
        assert first_post is not None
        assert first_post.content == "Содержимое 1"

    assert await clear_database(
        session_factory=test_session_maker,
        image_storage=storage,
    ) == (2, 4, 4)

    async with test_session_maker() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 0
        assert await session.scalar(select(func.count()).select_from(Post)) == 0


async def test_seed_rolls_back_data_and_images_on_download_error(test_session_maker, tmp_path):
    """Проверяет согласованную очистку файлов при сетевой ошибке."""

    storage = PostImageStorage(root=tmp_path)
    calls = 0

    def failing_loader(seed: str) -> bytes:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("Сервис изображений недоступен")
        return make_test_image(seed)

    with pytest.raises(RuntimeError, match="недоступен"):
        await seed_database(
            users_count=1,
            posts_per_user=2,
            password="demo-password",
            session_factory=test_session_maker,
            image_storage=storage,
            image_loader=failing_loader,
            text_loader=make_test_templates,
        )

    async with test_session_maker() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 0
        assert await session.scalar(select(func.count()).select_from(Post)) == 0
    assert list(storage.directory.glob("*.webp")) == []
