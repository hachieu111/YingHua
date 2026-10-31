"""Giai đoạn 6.5 (M16): lượt mini-game do máy chủ giữ.

- `minigame_rounds` (F16.01): mỗi lần dựng bộ chữ lưu một lượt (bộ thủ, chữ đã phát, giờ phát); nộp kết quả
  phải kèm mã lượt, nộp được đúng một lần (`submitted_at`).

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "minigame_rounds",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("radical", sa.String(length=8), nullable=False),
        sa.Column("chars", postgresql.ARRAY(sa.String(length=8)), nullable=False),
        sa.Column("issued_at", TS, nullable=False),
        sa.Column("submitted_at", TS, nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_minigame_rounds_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_minigame_rounds")),
    )
    op.create_index("ix_minigame_rounds_user_id_issued_at", "minigame_rounds", ["user_id", "issued_at"])


def downgrade() -> None:
    op.drop_index("ix_minigame_rounds_user_id_issued_at", table_name="minigame_rounds")
    op.drop_table("minigame_rounds")
