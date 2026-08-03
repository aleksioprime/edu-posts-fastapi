"""Локальное хранение и обработка изображений постов."""

import os
from io import BytesIO
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

MEDIA_ROOT = Path("media")
MEDIA_URL = "/media"
POST_IMAGE_MAX_BYTES = 5 * 1024 * 1024
POST_IMAGE_MAX_DIMENSION = 4096
POST_IMAGE_WEBP_QUALITY = 85


class PostImageStorage:
    """Проверяет и хранит изображения постов в локальной файловой системе."""

    allowed_formats = {"JPEG", "PNG", "WEBP"}

    def __init__(
        self,
        root: Path = MEDIA_ROOT,
        url_prefix: str = MEDIA_URL,
        max_bytes: int = POST_IMAGE_MAX_BYTES,
        max_dimension: int = POST_IMAGE_MAX_DIMENSION,
    ) -> None:
        """Подготавливает каталог хранения и ограничения изображений."""

        self.directory = Path(root) / "posts"
        self.url_prefix = url_prefix.rstrip("/")
        self.max_bytes = max_bytes
        self.max_dimension = max_dimension
        self.directory.mkdir(parents=True, exist_ok=True)

    async def save(self, post_id: UUID, upload: UploadFile) -> str:
        """Проверяет, преобразует и сохраняет загруженное изображение."""

        content = await upload.read(self.max_bytes + 1)
        if len(content) > self.max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Изображение не должно превышать {self.max_bytes // (1024 * 1024)} МБ",
            )
        if not content:
            raise HTTPException(status_code=422, detail="Передан пустой файл")

        await run_in_threadpool(self._validate_and_write, content, post_id)
        return self.url_for(post_id)

    def _validate_and_write(self, content: bytes, post_id: UUID) -> None:
        """Преобразует проверенное изображение в WebP и атомарно записывает его."""

        try:
            with Image.open(BytesIO(content)) as source:
                if source.format not in self.allowed_formats:
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail="Поддерживаются только JPEG, PNG и WebP",
                    )
                if source.width > self.max_dimension or source.height > self.max_dimension:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "Сторона изображения не должна превышать "
                            f"{self.max_dimension} пикселей"
                        ),
                    )
                source.load()

                image = source.convert("RGBA" if source.has_transparency_data else "RGB")
                target = self.path_for(post_id)
                temporary = target.with_suffix(".tmp")
                try:
                    image.save(
                        temporary,
                        format="WEBP",
                        quality=POST_IMAGE_WEBP_QUALITY,
                        method=6,
                    )
                    os.replace(temporary, target)
                finally:
                    temporary.unlink(missing_ok=True)
        except HTTPException:
            raise
        except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Файл не является корректным изображением") from exc

    def delete(self, post_id: UUID) -> None:
        """Удаляет изображение поста, если оно существует."""

        self.path_for(post_id).unlink(missing_ok=True)

    def clear(self) -> int:
        """Удаляет все изображения постов и возвращает их количество."""

        deleted = 0
        for path in self.directory.glob("*.webp"):
            path.unlink()
            deleted += 1
        return deleted

    def path_for(self, post_id: UUID) -> Path:
        """Строит путь к изображению поста."""

        return self.directory / f"{post_id}.webp"

    def url_for(self, post_id: UUID) -> str:
        """Строит публичный URL изображения поста."""

        return f"{self.url_prefix}/posts/{post_id}.webp"
