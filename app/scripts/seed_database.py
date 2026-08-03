"""Команда заполнения базы демонстрационными данными."""

import argparse
import asyncio
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import UUID

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import UploadFile
from sqlalchemy import or_, select

from src.core.database import async_session_maker
from src.models.post import Post
from src.models.user import User
from src.services.image_storage import POST_IMAGE_MAX_BYTES, PostImageStorage


PICSUM_SEEDED_IMAGE_URL = "https://picsum.photos/seed/{seed}/1200/800"
PICSUM_IMAGE_BY_ID_URL = "https://picsum.photos/id/{image_id}/1200/800"
PICSUM_LIST_URL = "https://picsum.photos/v2/list?page=1&limit=100"
EXTERNAL_REQUEST_TIMEOUT = 15
METADATA_DOWNLOAD_MAX_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class PostTemplate:
    """Текст тестового поста и связанное изображение."""

    title: str
    content: str
    image_url: str | None = None


def download_random_image(url: str) -> bytes:
    """Загружает изображение по подготовленному URL Lorem Picsum."""

    if not url.startswith("https://picsum.photos/"):
        raise RuntimeError("Разрешена загрузка изображений только из Lorem Picsum")
    request = Request(url, headers={"User-Agent": "edu-posts-seed/1.0"})
    try:
        with urlopen(request, timeout=EXTERNAL_REQUEST_TIMEOUT) as response:
            content = response.read(POST_IMAGE_MAX_BYTES + 1)
    except OSError as exc:
        raise RuntimeError(f"Не удалось загрузить тестовое изображение: {url}") from exc

    if len(content) > POST_IMAGE_MAX_BYTES:
        raise RuntimeError("Тестовое изображение превышает допустимые 5 МБ")
    if not content:
        raise RuntimeError("Сервис изображений вернул пустой ответ")
    return content


def download_post_templates() -> list[PostTemplate]:
    """Создаёт шаблоны постов из метаданных Lorem Picsum."""

    request = Request(
        PICSUM_LIST_URL,
        headers={"User-Agent": "edu-posts-seed/1.0"},
    )
    try:
        with urlopen(request, timeout=EXTERNAL_REQUEST_TIMEOUT) as response:
            content = response.read(METADATA_DOWNLOAD_MAX_BYTES + 1)
    except OSError as exc:
        raise RuntimeError("Не удалось загрузить метаданные Lorem Picsum") from exc

    if len(content) > METADATA_DOWNLOAD_MAX_BYTES:
        raise RuntimeError("Ответ Lorem Picsum превышает допустимый 1 МБ")

    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("Lorem Picsum вернул некорректный JSON") from exc

    if not isinstance(payload, list):
        raise RuntimeError("Lorem Picsum вернул неожиданный формат данных")

    templates = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        image_id = str(item.get("id", "")).strip()
        author = str(item.get("author", "")).strip()[:120]
        source_url = str(item.get("url", "")).strip()
        try:
            width = int(item["width"])
            height = int(item["height"])
        except (KeyError, TypeError, ValueError):
            continue
        if not image_id or not author or width <= 0 or height <= 0:
            continue
        if not source_url.startswith("https://"):
            continue

        templates.append(
            PostTemplate(
                title=f"Фотография #{image_id} — {author}"[:200],
                content=(
                    f"Фотография автора {author}. "
                    f"Размер оригинала: {width} × {height}. "
                    f"Источник: {source_url}"
                ),
                image_url=PICSUM_IMAGE_BY_ID_URL.format(
                    image_id=quote(image_id, safe=""),
                ),
            )
        )

    if not templates:
        raise RuntimeError("Lorem Picsum не вернул подходящих метаданных")
    return templates


def make_local_template(user_number: int, post_number: int, username: str) -> PostTemplate:
    """Создаёт локальный текст поста без обращения к внешнему API."""

    return PostTemplate(
        title=f"Тестовый пост {user_number}.{post_number}",
        content=(
            f"Тестовая публикация №{post_number} пользователя {username}. "
            "Эти данные созданы скриптом seed_database.py."
        ),
    )


async def seed_database(
    users_count: int,
    posts_per_user: int,
    password: str,
    session_factory=async_session_maker,
    image_storage: PostImageStorage | None = None,
    image_loader: Callable[[str], bytes] = download_random_image,
    text_loader: Callable[[], list[PostTemplate]] = download_post_templates,
    add_images: bool = True,
    use_remote_text: bool = True,
) -> tuple[int, int]:
    """Идемпотентно создаёт demo-пользователей, посты и изображения."""

    created_users = 0
    created_posts = 0
    created_image_ids: list[UUID] = []
    storage = image_storage
    if add_images and storage is None:
        storage = PostImageStorage()
    templates = (
        await asyncio.to_thread(text_loader)
        if use_remote_text and users_count > 0 and posts_per_user > 0
        else []
    )

    try:
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
                    if templates:
                        # Индекс не зависит от числа постов в запуске, поэтому повторный
                        # seed с другим --posts-per-user остаётся идемпотентным.
                        template_index = ((user_number - 1) * 50 + post_number - 1) % len(
                            templates
                        )
                        template = templates[template_index]
                    else:
                        template = make_local_template(user_number, post_number, username)

                    exists = await session.scalar(
                        select(Post.id).where(
                            Post.author_id == user.id,
                            Post.title == template.title,
                        )
                    )
                    if exists is not None:
                        continue

                    post = Post(
                        title=template.title,
                        content=template.content,
                        author_id=user.id,
                    )
                    session.add(post)
                    await session.flush()

                    if add_images and storage is not None:
                        image_url = template.image_url or PICSUM_SEEDED_IMAGE_URL.format(
                            seed=quote(str(post.id), safe=""),
                        )
                        content = await asyncio.to_thread(image_loader, image_url)
                        upload = UploadFile(file=BytesIO(content), filename=f"{post.id}.jpg")
                        try:
                            post.image_url = await storage.save(post.id, upload)
                        finally:
                            await upload.close()
                        created_image_ids.append(post.id)

                    created_posts += 1

            await session.commit()
    except Exception:
        # Файлы не участвуют в транзакции БД, поэтому удаляем их при любом сбое.
        if storage is not None:
            for post_id in created_image_ids:
                storage.delete(post_id)
        raise

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
    parser.add_argument(
        "--without-images",
        action="store_true",
        help="Создать посты без загрузки изображений из Lorem Picsum.",
    )
    parser.add_argument(
        "--local-text",
        action="store_true",
        help="Создать встроенные русские тексты без загрузки метаданных Lorem Picsum.",
    )
    args = parser.parse_args()

    if not 1 <= args.users <= 20:
        parser.error("--users должен быть от 1 до 20")
    if not 0 <= args.posts_per_user <= 50:
        parser.error("--posts-per-user должен быть от 0 до 50")
    if len(args.password) < 8:
        parser.error("--password должен содержать не менее 8 символов")

    users, posts = asyncio.run(
        seed_database(
            args.users,
            args.posts_per_user,
            args.password,
            add_images=not args.without_images,
            use_remote_text=not args.local_text,
        )
    )
    print(f"Тестовые данные готовы: создано пользователей — {users}, постов — {posts}")
    print(f"Логины: demo1 … demo{args.users}; общий пароль передан через --password")
