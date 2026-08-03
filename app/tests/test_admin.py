from src.admin import auth as admin_auth_module
from src.models.user import User


async def test_admin_requires_superuser(client, auth_headers, monkeypatch, test_session_maker):
    monkeypatch.setattr(admin_auth_module, "async_session_maker", test_session_maker)

    regular_login = await client.post(
        "/admin/login",
        data={"username": "author", "password": "strong-password"},
        follow_redirects=False,
    )
    assert regular_login.status_code == 400

    async with test_session_maker() as session:
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password="",
            is_superuser=True,
        )
        admin.set_password("admin-password")
        session.add(admin)
        await session.commit()

    admin_login = await client.post(
        "/admin/login",
        data={"username": "admin", "password": "admin-password"},
        follow_redirects=False,
    )
    assert admin_login.status_code == 302

    dashboard = await client.get("/admin/", follow_redirects=False)
    assert dashboard.status_code == 200
