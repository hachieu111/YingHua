"""M02: hướng dẫn người mới có lựa chọn "không nhắc lại" lưu ở máy chủ (F02.05).

- `user_settings.dismissed_tours`: mảng khóa hướng dẫn đã tắt (`home`, `reader`), mặc định rỗng.

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column(
            "dismissed_tours",
            postgresql.ARRAY(sa.String(length=16)),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "dismissed_tours")
