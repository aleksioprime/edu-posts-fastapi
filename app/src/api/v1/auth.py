from typing import Annotated

from fastapi import APIRouter, Depends, Form, status

from src.dependencies import get_auth_service
from src.schemas.auth import Token
from src.schemas.user import UserCreate, UserMe
from src.services.auth import AuthService


router = APIRouter()


@router.post("/register", response_model=UserMe, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, service: AuthService = Depends(get_auth_service)):
    return await service.register(data)


@router.post("/login", response_model=Token)
async def login(
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    service: AuthService = Depends(get_auth_service),
):
    """OAuth2-совместимый вход. В поле username можно передать логин или email."""
    return await service.login(username, password)

