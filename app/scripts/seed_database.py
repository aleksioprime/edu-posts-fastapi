"""Команда заполнения базы демонстрационными данными."""

import argparse
import asyncio
import hashlib
import json
import re
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from uuid import UUID

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import UploadFile
from faker import Faker
from PIL import Image, ImageDraw
from sqlalchemy import or_, select

from src.core.database import async_session_maker
from src.models.post import Post
from src.models.user import User
from src.services.image_storage import POST_IMAGE_MAX_BYTES, PostImageStorage


DUMMYJSON_POSTS_URL = "https://dummyjson.com/posts?limit=50&select=title,body"
PLACEHOLD_IMAGE_URL = "https://placehold.co/1200x800/1f2937/ffffff.png?text={text}"
EXTERNAL_REQUEST_TIMEOUT = 30
EXTERNAL_REQUEST_ATTEMPTS = 3
POSTS_DOWNLOAD_MAX_BYTES = 1024 * 1024
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; edu-posts-seed/1.0)",
    "Accept-Encoding": "identity",
    "Connection": "close",
}
FAKER_SEED = 20250803
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")
IMAGE_TITLE_ADJECTIVES = (
    "Azure",
    "Bright",
    "Calm",
    "Crystal",
    "Golden",
    "Hidden",
    "Lunar",
    "Misty",
    "Quiet",
    "Silver",
    "Solar",
    "Wild",
)
IMAGE_TITLE_NOUNS = (
    "Dawn",
    "Forest",
    "Garden",
    "Harbor",
    "Horizon",
    "Journey",
    "Meadow",
    "Ocean",
    "River",
    "Sky",
    "Valley",
    "Vista",
)


def _download(url: str, accept: str, max_bytes: int) -> bytes:
    """Загружает ограниченный ответ с повторными попытками при сетевых ошибках."""

    last_error: OSError | None = None
    for attempt in range(EXTERNAL_REQUEST_ATTEMPTS):
        request = Request(url, headers={**HTTP_HEADERS, "Accept": accept})
        try:
            with urlopen(request, timeout=EXTERNAL_REQUEST_TIMEOUT) as response:
                return response.read(max_bytes + 1)
        except OSError as exc:
            last_error = exc
            if attempt < EXTERNAL_REQUEST_ATTEMPTS - 1:
                time.sleep(2**attempt)

    if last_error is None:  # pragma: no cover — цикл всегда выполняется хотя бы один раз.
        raise RuntimeError("Не удалось выполнить внешний запрос")
    raise last_error


@dataclass(frozen=True, slots=True)
class PostTemplate:
    """Текст тестового поста и URL изображения-заглушки."""

    title: str
    content: str
    image_url: str | None = None


@dataclass(frozen=True, slots=True)
class UserTemplate:
    """Логин и безопасный тестовый email пользователя."""

    username: str
    email: str


def generate_user_templates(users_count: int) -> list[UserTemplate]:
    """Генерирует воспроизводимые уникальные реквизиты через Faker."""

    faker = Faker("en_US")
    faker.seed_instance(FAKER_SEED)
    templates = []
    usernames = set()
    while len(templates) < users_count:
        username = faker.unique.user_name().lower()[:50]
        if not USERNAME_PATTERN.fullmatch(username) or username in usernames:
            continue
        usernames.add(username)
        templates.append(
            UserTemplate(
                username=username,
                email=f"{username}@example.com",
            )
        )
    return templates


def generate_image_title(seed: str) -> str:
    """Генерирует короткое воспроизводимое название изображения."""

    faker = Faker("en_US")
    faker.seed_instance(f"{FAKER_SEED}:image:{seed}")
    adjective = faker.random_element(IMAGE_TITLE_ADJECTIVES)
    noun = faker.random_element(IMAGE_TITLE_NOUNS)
    return f"{adjective} {noun}"


def download_placeholder_image(url: str) -> bytes:
    """Загружает изображение-заглушку из Placehold.co."""

    if not url.startswith("https://placehold.co/"):
        raise RuntimeError("Разрешена загрузка изображений только из Placehold.co")
    try:
        content = _download(url, "image/*", POST_IMAGE_MAX_BYTES)
    except OSError as exc:
        raise RuntimeError(f"Не удалось загрузить изображение из Placehold.co: {url}") from exc

    if len(content) > POST_IMAGE_MAX_BYTES:
        raise RuntimeError("Тестовое изображение превышает допустимые 5 МБ")
    if not content:
        raise RuntimeError("Сервис изображений вернул пустой ответ")
    return content


def generate_local_image(seed: str) -> bytes:
    """Создаёт воспроизводимую заглушку изображения по идентификатору поста."""

    digest = hashlib.sha256(seed.encode()).digest()
    background = tuple(digest[index] for index in range(3))
    accent = tuple(digest[index] for index in range(3, 6))
    image = Image.new("RGB", (1200, 800), color=background)
    drawing = ImageDraw.Draw(image)
    drawing.rectangle((80, 80, 1120, 720), outline=accent, width=24)
    drawing.text((120, 120), "Edu Posts", fill=(255, 255, 255))

    content = BytesIO()
    image.save(content, format="JPEG", quality=85)
    return content.getvalue()


def download_post_templates() -> list[PostTemplate]:
    """Создаёт шаблоны постов из ответа DummyJSON."""

    try:
        content = _download(
            DUMMYJSON_POSTS_URL,
            "application/json",
            POSTS_DOWNLOAD_MAX_BYTES,
        )
    except OSError as exc:
        raise RuntimeError("Не удалось загрузить тексты из DummyJSON") from exc

    if len(content) > POSTS_DOWNLOAD_MAX_BYTES:
        raise RuntimeError("Ответ DummyJSON превышает допустимый 1 МБ")

    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("DummyJSON вернул некорректный JSON") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("posts"), list):
        raise RuntimeError("DummyJSON вернул неожиданный формат данных")

    templates = []
    for number, item in enumerate(payload["posts"], start=1):
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        body = item.get("body")
        if not isinstance(title, str) or not title.strip():
            continue
        if not isinstance(body, str) or not body.strip():
            continue

        post_id = str(item.get("id", number)).strip() or str(number)
        normalized_title = title.strip()

        templates.append(
            PostTemplate(
                title=(normalized_title[:1].upper() + normalized_title[1:])[:200],
                content=body.strip(),
                image_url=PLACEHOLD_IMAGE_URL.format(
                    text=quote_plus(generate_image_title(post_id)),
                ),
            )
        )

    if not templates:
        raise RuntimeError("DummyJSON не вернул подходящих постов")
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
    image_loader: Callable[[str], bytes] = download_placeholder_image,
    text_loader: Callable[[], list[PostTemplate]] = download_post_templates,
    add_images: bool = True,
    use_remote_text: bool = True,
    fallback_on_external_error: bool = True,
) -> tuple[int, int]:
    """Идемпотентно создаёт demo-пользователей, посты и изображения."""

    created_users = 0
    created_posts = 0
    created_image_ids: list[UUID] = []
    storage = image_storage
    if add_images and storage is None:
        storage = PostImageStorage()
    templates = []
    image_service_available = True
    user_templates = generate_user_templates(users_count)
    if use_remote_text and users_count > 0 and posts_per_user > 0:
        try:
            templates = await asyncio.to_thread(text_loader)
        except RuntimeError as exc:
            if not fallback_on_external_error:
                raise
            print(
                f"Предупреждение: {exc}. Используются локальные тексты.",
                file=sys.stderr,
            )

    try:
        async with session_factory() as session:
            for user_number in range(1, users_count + 1):
                user_template = user_templates[user_number - 1]
                username = user_template.username
                email = user_template.email
                user = await session.scalar(
                    select(User).where(or_(User.username == username, User.email == email))
                )

                if user is None:
                    legacy_username = f"demo{user_number}"
                    legacy_email = f"demo{user_number}@example.com"
                    user = await session.scalar(
                        select(User).where(
                            User.username == legacy_username,
                            User.email == legacy_email,
                        )
                    )
                    if user is not None:
                        user.username = username
                        user.email = email

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
                        image_url = template.image_url or PLACEHOLD_IMAGE_URL.format(
                            text=quote_plus(generate_image_title(str(post.id))),
                        )
                        if image_service_available:
                            try:
                                content = await asyncio.to_thread(image_loader, image_url)
                            except RuntimeError as exc:
                                if not fallback_on_external_error:
                                    raise
                                print(
                                    f"Предупреждение: {exc}. "
                                    "Остальные изображения создаются локально.",
                                    file=sys.stderr,
                                )
                                image_service_available = False
                                content = await asyncio.to_thread(
                                    generate_local_image,
                                    str(post.id),
                                )
                        else:
                            content = await asyncio.to_thread(
                                generate_local_image,
                                str(post.id),
                            )
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
        help="Создать посты без загрузки изображений из Placehold.co.",
    )
    parser.add_argument(
        "--local-text",
        action="store_true",
        help="Создать встроенные русские тексты без обращения к DummyJSON.",
    )
    parser.add_argument(
        "--strict-external",
        action="store_true",
        help="Прервать заполнение, если DummyJSON или Placehold.co недоступны.",
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
            fallback_on_external_error=not args.strict_external,
        )
    )
    print(f"Тестовые данные готовы: создано пользователей — {users}, постов — {posts}")
    usernames = ", ".join(
        template.username for template in generate_user_templates(args.users)
    )
    print(f"Логины: {usernames}; общий пароль передан через --password")
