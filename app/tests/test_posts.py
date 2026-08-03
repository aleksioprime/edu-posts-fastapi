from io import BytesIO

from PIL import Image


def make_image() -> bytes:
    content = BytesIO()
    Image.new("RGBA", (64, 48), color=(45, 110, 180, 180)).save(content, format="PNG")
    return content.getvalue()


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
    assert response.json()["image_url"] is None

    response = await client.get("/api/v1/posts")
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = await client.get(f"/api/v1/posts/{post_id}")
    assert response.status_code == 200
    assert response.json()["author"]["username"] == "author"


async def test_owner_can_upload_serve_and_delete_image(client, auth_headers):
    post = await client.post(
        "/api/v1/posts",
        json={"title": "Пост с изображением", "content": "Текст"},
        headers=auth_headers,
    )
    post_id = post.json()["id"]

    response = await client.put(
        f"/api/v1/posts/{post_id}/image",
        files={"image": ("cover.png", make_image(), "image/png")},
        headers=auth_headers,
    )
    assert response.status_code == 200
    image_url = response.json()["image_url"]
    assert image_url == f"/media/posts/{post_id}.webp"

    image = await client.get(image_url)
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/webp"

    response = await client.delete(f"/api/v1/posts/{post_id}/image", headers=auth_headers)
    assert response.status_code == 204
    assert (await client.get(image_url)).status_code == 404
    assert (await client.get(f"/api/v1/posts/{post_id}")).json()["image_url"] is None


async def test_image_validation_and_permissions(client, auth_headers):
    post = await client.post(
        "/api/v1/posts",
        json={"title": "Защищённый пост", "content": "Текст"},
        headers=auth_headers,
    )
    post_id = post.json()["id"]

    invalid = await client.put(
        f"/api/v1/posts/{post_id}/image",
        files={"image": ("not-image.txt", b"not an image", "text/plain")},
        headers=auth_headers,
    )
    assert invalid.status_code == 422

    await client.post(
        "/api/v1/auth/register",
        json={"username": "image_thief", "email": "thief@example.com", "password": "secure-password"},
    )
    login = await client.post(
        "/api/v1/auth/login", data={"username": "image_thief", "password": "secure-password"}
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    forbidden = await client.put(
        f"/api/v1/posts/{post_id}/image",
        files={"image": ("cover.png", make_image(), "image/png")},
        headers=other_headers,
    )
    assert forbidden.status_code == 403


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
