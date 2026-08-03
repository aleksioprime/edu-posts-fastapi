from io import BytesIO
from urllib.parse import quote_plus

import pytest
from PIL import Image
from sqlalchemy import func, select

from scripts.clear_database import clear_database
from scripts.seed_database import (
    USERNAME_PATTERN,
    PostTemplate,
    generate_image_title,
    generate_user_templates,
    download_post_templates,
    seed_database,
)
from src.models.post import Post
from src.models.user import User
from src.services.image_storage import PostImageStorage


def make_test_image(_: str) -> bytes:
    """Создаёт изображение без обращения к внешнему API."""

    content = BytesIO()
    Image.new("RGB", (80, 60), color=(90, 140, 70)).save(content, format="JPEG")
    return content.getvalue()


def make_test_templates() -> list[PostTemplate]:
    """Возвращает предсказуемые метаданные без обращения к внешнему API."""

    return [
        PostTemplate(
            title=f"Фотография #{number} — Автор {number}",
            content=(
                f"Фотография автора Автор {number}. "
                "Размер оригинала: 1200 × 800. "
                f"Источник: https://example.com/photo/{number}"
            ),
            image_url=f"https://placehold.co/1200x800/png?text=Post+{number}",
        )
        for number in range(1, 101)
    ]


def test_user_templates_are_unique_valid_and_reproducible():
    """Проверяет стабильность и допустимый формат логинов Faker."""

    first = generate_user_templates(20)
    second = generate_user_templates(20)

    assert first == second
    assert len({template.username for template in first}) == 20
    assert all(USERNAME_PATTERN.fullmatch(template.username) for template in first)
    assert all(template.email == f"{template.username}@example.com" for template in first)


def test_image_titles_are_random_looking_and_reproducible():
    """Проверяет стабильность и разнообразие названий изображений."""

    first = [generate_image_title(str(number)) for number in range(1, 6)]
    second = [generate_image_title(str(number)) for number in range(1, 6)]

    assert first == second
    assert len(set(first)) == 5
    assert all(len(title.split()) == 2 for title in first)
    assert all(not title.startswith("Post ") for title in first)


def test_download_post_templates_validates_and_normalizes_response(monkeypatch):
    """Проверяет преобразование ответа DummyJSON в шаблоны."""

    response = BytesIO(
        b'{"posts":[{"id":42,"title":" Example title ",'
        b'"body":"Example content"}],"total":1,"skip":0,"limit":1}'
    )
    monkeypatch.setattr(
        "scripts.seed_database.urlopen",
        lambda request, timeout: response,
    )

    assert download_post_templates() == [
        PostTemplate(
            title="Example title",
            content="Example content",
            image_url=(
                "https://placehold.co/1200x800/1f2937/ffffff.png?text="
                + quote_plus(generate_image_title("42"))
            ),
        )
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
        usernames = set((await session.scalars(select(User.username))).all())
        assert usernames == {
            template.username for template in generate_user_templates(2)
        }
        assert await session.scalar(
            select(func.count()).select_from(Post).where(Post.image_url.is_not(None))
        ) == 4
        first_post = await session.scalar(
            select(Post).where(Post.title == "Фотография #1 — Автор 1")
        )
        assert first_post is not None
        assert "Размер оригинала: 1200 × 800" in first_post.content
        assert "https://example.com/photo/1" in first_post.content

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
            fallback_on_external_error=False,
        )

    async with test_session_maker() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 0
        assert await session.scalar(select(func.count()).select_from(Post)) == 0
    assert list(storage.directory.glob("*.webp")) == []


async def test_seed_uses_local_fallback_when_services_are_unavailable(
    test_session_maker,
    tmp_path,
):
    """Проверяет локальную генерацию при недоступности внешних сервисов."""

    storage = PostImageStorage(root=tmp_path)

    def unavailable_templates() -> list[PostTemplate]:
        raise RuntimeError("DummyJSON недоступен")

    def unavailable_image(_: str) -> bytes:
        raise RuntimeError("Placehold.co недоступен")

    created = await seed_database(
        users_count=1,
        posts_per_user=2,
        password="demo-password",
        session_factory=test_session_maker,
        image_storage=storage,
        image_loader=unavailable_image,
        text_loader=unavailable_templates,
    )

    assert created == (1, 2)
    async with test_session_maker() as session:
        posts = list((await session.scalars(select(Post).order_by(Post.title))).all())
    assert [post.title for post in posts] == ["Тестовый пост 1.1", "Тестовый пост 1.2"]
    assert all(post.image_url for post in posts)
    assert len(list(storage.directory.glob("*.webp"))) == 2


async def test_seed_renames_legacy_demo_user_without_losing_posts(test_session_maker):
    """Проверяет обновление старого demo-логина без создания дубля."""

    async with test_session_maker() as session:
        user = User(username="demo1", email="demo1@example.com", hashed_password="")
        user.set_password("old-password")
        session.add(user)
        await session.flush()
        session.add(Post(title="Старый пост", content="Содержимое", author_id=user.id))
        await session.commit()

    created = await seed_database(
        users_count=1,
        posts_per_user=0,
        password="demo-password",
        session_factory=test_session_maker,
        add_images=False,
        use_remote_text=False,
    )

    assert created == (0, 0)
    expected = generate_user_templates(1)[0]
    async with test_session_maker() as session:
        user = await session.scalar(select(User))
        assert user is not None
        assert user.username == expected.username
        assert user.email == expected.email
        assert await session.scalar(select(func.count()).select_from(Post)) == 1


async def test_clear_preserves_superuser_but_removes_all_posts(test_session_maker):
    """Проверяет сохранение администратора при полной очистке публикаций."""

    async with test_session_maker() as session:
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password="",
            is_superuser=True,
        )
        regular = User(
            username="regular",
            email="regular@example.com",
            hashed_password="",
        )
        session.add_all([admin, regular])
        await session.flush()
        session.add_all(
            [
                Post(title="Пост администратора", content="Текст", author_id=admin.id),
                Post(title="Обычный пост", content="Текст", author_id=regular.id),
            ]
        )
        await session.commit()

    assert await clear_database(session_factory=test_session_maker) == (1, 2, 0)

    async with test_session_maker() as session:
        users = list((await session.scalars(select(User))).all())
        assert len(users) == 1
        assert users[0].username == "admin"
        assert users[0].is_superuser is True
        assert await session.scalar(select(func.count()).select_from(Post)) == 0
