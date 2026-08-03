"""HTTP-эндпоинты для работы с постами и их изображениями."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status

from src.core.security import get_current_user
from src.dependencies import get_post_service
from src.models.user import User
from src.schemas.post import PostCreate, PostList, PostRead, PostUpdate
from src.services.posts import PostService


router = APIRouter()


@router.get("", response_model=PostList)
async def list_posts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: PostService = Depends(get_post_service),
):
    """Возвращает публичный список постов с пагинацией."""

    return await service.get_all(limit, offset)


@router.get("/mine", response_model=PostList)
async def list_my_posts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    """Возвращает посты текущего пользователя с пагинацией."""

    return await service.get_all(limit, offset, author_id=user.id)


@router.get("/{post_id}", response_model=PostRead)
async def get_post(post_id: UUID, service: PostService = Depends(get_post_service)):
    """Возвращает один публичный пост."""

    return await service.get_by_id(post_id)


@router.post("", response_model=PostRead, status_code=status.HTTP_201_CREATED)
async def create_post(
    data: PostCreate,
    user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    """Создаёт пост текущего пользователя."""

    return await service.create(data, user)


@router.patch("/{post_id}", response_model=PostRead)
async def update_post(
    post_id: UUID,
    data: PostUpdate,
    user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    """Обновляет пост его автора или суперпользователя."""

    return await service.update(post_id, data, user)


@router.put("/{post_id}/image", response_model=PostRead)
async def upload_post_image(
    post_id: UUID,
    image: UploadFile = File(description="Изображение JPEG, PNG или WebP размером до 5 МБ"),
    user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    """Загружает или заменяет изображение поста."""

    return await service.upload_image(post_id, image, user)


@router.delete("/{post_id}/image", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post_image(
    post_id: UUID,
    user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    """Удаляет изображение поста."""

    await service.delete_image(post_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: UUID,
    user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    """Удаляет пост и связанное с ним изображение."""

    await service.delete(post_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
