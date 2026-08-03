"""Создание и настройка FastAPI-приложения."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.admin import setup_admin
from src.api.v1 import router as api_v1_router
from src.core.config import settings
from src.services.image_storage import MEDIA_ROOT, MEDIA_URL


app = FastAPI(
    title=settings.project_name,
    description=settings.project_description,
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_v1_router, prefix="/api/v1")
setup_admin(app)

Path(MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
app.mount(
    MEDIA_URL,
    StaticFiles(directory=MEDIA_ROOT),
    name="media",
)


@app.get("/health", tags=["system"])
async def health():
    """Подтверждает доступность приложения."""

    return {"status": "ok"}
