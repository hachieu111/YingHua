"""Giai đoạn 6 (đợt A2): cấu hình hệ thống, gỡ nội dung và ảnh đại diện có sẵn.

- `system_settings` (F13.05): công tắc LLM/TTS, hạn mức, chế độ bảo trì, kiểm duyệt ảnh tự động, OCR khi tải,
  thông báo quản trị, trang pháp lý, trang mẫu… lưu theo khóa; giá trị JSONB.
- `content_removals` (F13.04): nhật ký gỡ ảnh/trang vi phạm.
- `users.avatar_preset` (F01.10 mở rộng, US-NH-65 TC6): mã ảnh đại diện mặc định,
  loại trừ với `avatar_file_id`.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=48), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name=op.f("fk_system_settings_updated_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_system_settings")),
    )
    op.create_table(
        "content_removals",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("file_id", sa.BigInteger(), nullable=True),
        sa.Column("page_id", sa.BigInteger(), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("removed_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["stored_files.id"],
            name=op.f("fk_content_removals_file_id_stored_files"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["page_id"], ["pages.id"], name=op.f("fk_content_removals_page_id_pages"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["removed_by"],
            ["users.id"],
            name=op.f("fk_content_removals_removed_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_removals")),
    )
    op.create_index(op.f("ix_content_removals_created_at"), "content_removals", ["created_at"])
    op.add_column("users", sa.Column("avatar_preset", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_preset")
    op.drop_index(op.f("ix_content_removals_created_at"), table_name="content_removals")
    op.drop_table("content_removals")
    op.drop_table("system_settings")
