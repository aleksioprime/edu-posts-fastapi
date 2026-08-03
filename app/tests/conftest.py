import os
import shutil
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-with-safe-length"
os.environ["ADMIN_SESSION_SECRET"] = "test-admin-key-with-safe-length"

TEST_MEDIA_ROOT = Path("tests/.media")
TEST_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

from src.core.database import Base, get_session
from src.dependencies import get_image_storage
from src.main import app
from src.services.image_storage import PostImageStorage


test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_session():
    """Предоставляет API изолированную тестовую сессию базы данных."""

    async with TestSession() as session:
        yield session


def override_image_storage() -> PostImageStorage:
    """Направляет тестовые изображения в отдельный каталог."""

    return PostImageStorage(root=TEST_MEDIA_ROOT)


app.dependency_overrides[get_session] = override_session
app.dependency_overrides[get_image_storage] = override_image_storage

# Статические файлы и хранилище должны смотреть в один тестовый каталог.
media_route = next(
    route for route in app.routes if isinstance(route, Mount) and route.name == "media"
)
media_route.app = StaticFiles(directory=TEST_MEDIA_ROOT)


@pytest_asyncio.fixture(autouse=True)
async def database():
    shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
    TEST_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value


@pytest_asyncio.fixture
def test_session_maker():
    return TestSession


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient):
    registration = {
        "username": "author",
        "email": "author@example.com",
        "password": "strong-password",
    }
    response = await client.post("/api/v1/auth/register", json=registration)
    assert response.status_code == 201
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": registration["username"], "password": registration["password"]},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
