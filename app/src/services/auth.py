from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from src.core.security import create_access_token
from src.models.user import User
from src.repositories.uow import UnitOfWork
from src.schemas.auth import Token
from src.schemas.user import UserCreate


class AuthService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def register(self, data: UserCreate) -> User:
        user = User(username=data.username, email=str(data.email).lower(), hashed_password="")
        user.set_password(data.password)
        try:
            await self.uow.users.create(user)
            await self.uow.commit()
        except IntegrityError as exc:
            await self.uow.rollback()
            raise HTTPException(status_code=409, detail="Имя пользователя или email уже заняты") from exc
        return user

    async def login(self, login: str, password: str) -> Token:
        user = await self.uow.users.get_by_login(login)
        if user is None or not user.is_active or not user.check_password(password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return Token(access_token=create_access_token(user.id))

