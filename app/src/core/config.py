from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = "Edu Posts API"
    project_description: str = "Учебный API публикаций на FastAPI"
    database_url: str = "sqlite+aiosqlite:///./posts.db"
    show_sql: bool = False

    jwt_secret_key: str = Field(default="dev-secret-change-me", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    admin_session_secret: str = Field(default="dev-admin-secret", min_length=16)

    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

