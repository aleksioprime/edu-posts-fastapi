"""HTTP-эндпоинты текущего пользователя."""

from fastapi import APIRouter, Depends

from src.core.security import get_current_user
from src.models.user import User
from src.schemas.user import UserMe


router = APIRouter()


@router.get("/me", response_model=UserMe)
async def get_me(user: User = Depends(get_current_user)):
    """Возвращает профиль текущего пользователя."""

    return user
