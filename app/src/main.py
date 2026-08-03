from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.admin import setup_admin
from src.api.v1 import router as api_v1_router
from src.core.config import settings


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


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}

