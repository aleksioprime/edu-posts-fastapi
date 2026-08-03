"""Добавление URL изображения к постам."""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_post_image"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет постам необязательный URL изображения."""

    op.add_column("posts", sa.Column("image_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Удаляет URL изображения из постов."""

    op.drop_column("posts", "image_url")
