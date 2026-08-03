async def test_posts_are_public_but_creation_requires_auth(client, auth_headers):
    response = await client.post("/api/v1/posts", json={"title": "Первый пост", "content": "Текст"})
    assert response.status_code == 401

    response = await client.post(
        "/api/v1/posts",
        json={"title": "Первый пост", "content": "Текст"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    post_id = response.json()["id"]

    response = await client.get("/api/v1/posts")
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = await client.get(f"/api/v1/posts/{post_id}")
    assert response.status_code == 200
    assert response.json()["author"]["username"] == "author"


async def test_only_owner_can_update_or_delete_post(client, auth_headers):
    response = await client.post(
        "/api/v1/posts",
        json={"title": "Исходный", "content": "Текст"},
        headers=auth_headers,
    )
    post_id = response.json()["id"]

    await client.post(
        "/api/v1/auth/register",
        json={"username": "another", "email": "another@example.com", "password": "secure-password"},
    )
    login = await client.post(
        "/api/v1/auth/login", data={"username": "another", "password": "secure-password"}
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    forbidden = await client.patch(
        f"/api/v1/posts/{post_id}", json={"title": "Чужое изменение"}, headers=other_headers
    )
    assert forbidden.status_code == 403

    updated = await client.patch(
        f"/api/v1/posts/{post_id}", json={"title": "Обновлённый"}, headers=auth_headers
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Обновлённый"

    deleted = await client.delete(f"/api/v1/posts/{post_id}", headers=auth_headers)
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/posts/{post_id}")).status_code == 404

