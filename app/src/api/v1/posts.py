from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

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
    return await service.get_all(limit, offset)


@router.get("/{post_id}", response_model=PostRead)
async def get_post(post_id: UUID, service: PostService = Depends(get_post_service)):
    return await service.get_by_id(post_id)


@router.post("", response_model=PostRead, status_code=status.HTTP_201_CREATED)
async def create_post(
    data: PostCreate,
    user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    return await service.create(data, user)


@router.patch("/{post_id}", response_model=PostRead)
async def update_post(
    post_id: UUID,
    data: PostUpdate,
    user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    return await service.update(post_id, data, user)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: UUID,
    user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    await service.delete(post_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

