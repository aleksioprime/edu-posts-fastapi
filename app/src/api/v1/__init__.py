from fastapi import APIRouter

from src.api.v1.auth import router as auth_router
from src.api.v1.posts import router as posts_router
from src.api.v1.users import router as users_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(posts_router, prefix="/posts", tags=["posts"])

