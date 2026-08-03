import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-with-safe-length"
os.environ["ADMIN_SESSION_SECRET"] = "test-admin-key-with-safe-length"

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.core.database import Base, get_session
from src.main import app


test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_session():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_session] = override_session


@pytest_asyncio.fixture(autouse=True)
async def database():
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


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
