async def test_register_login_and_me(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "student",
            "email": "student@example.com",
            "password": "secure-password",
        },
    )
    assert response.status_code == 201
    assert response.json()["username"] == "student"
    assert "password" not in response.json()

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "student", "password": "secure-password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "student@example.com"


async def test_duplicate_registration_returns_conflict(client):
    body = {"username": "student", "email": "student@example.com", "password": "secure-password"}
    assert (await client.post("/api/v1/auth/register", json=body)).status_code == 201
    assert (await client.post("/api/v1/auth/register", json=body)).status_code == 409

