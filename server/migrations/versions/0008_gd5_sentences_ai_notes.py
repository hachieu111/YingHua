"""Giai đoạn 5 (bổ sung): câu thoại đã lưu, Thẻ mở rộng AI và cỡ chữ bong bóng.

- `saved_sentences` (F07.11, US-NH-70): bản sao văn bản của câu thoại, UQ (user_id, bubble_id).
- `vocab_ai_notes` (F08.11, US-NH-75): bộ đệm nội dung AI cho mỗi mục từ, xóa theo mục từ.
- `user_settings.bubble_font_scale` (F02.04, US-NH-74): cỡ chữ lớp dịch, 80..160 (bước 10 kiểm ở ứng dụng).

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_sentences",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("bubble_id", sa.BigInteger(), nullable=True),
        sa.Column("page_id", sa.BigInteger(), nullable=True),
        sa.Column("sentence_zh", sa.Text(), nullable=False),
        sa.Column("sentence_vi", sa.Text(), nullable=True),
        sa.Column("source_label", sa.String(length=255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_saved_sentences_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["bubble_id"], ["bubbles.id"], name=op.f("fk_saved_sentences_bubble_id_bubbles"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["page_id"], ["pages.id"], name=op.f("fk_saved_sentences_page_id_pages"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_saved_sentences")),
        sa.UniqueConstraint("user_id", "bubble_id", name=op.f("uq_saved_sentences_user_id_bubble_id")),
    )
    op.create_index(
        "ix_saved_sentences_user_id_created_at", "saved_sentences", ["user_id", "created_at"], unique=False
    )
    op.create_table(
        "vocab_ai_notes",
        sa.Column("vocab_entry_id", sa.BigInteger(), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=12), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("regenerate_count", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint("source IN ('llm', 'fallback')", name=op.f("ck_vocab_ai_notes_source")),
        sa.ForeignKeyConstraint(
            ["vocab_entry_id"],
            ["vocab_entries.id"],
            name=op.f("fk_vocab_ai_notes_vocab_entry_id_vocab_entries"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("vocab_entry_id", name=op.f("pk_vocab_ai_notes")),
    )
    op.add_column(
        "user_settings",
        sa.Column("bubble_font_scale", sa.SmallInteger(), server_default=sa.text("100"), nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_user_settings_bubble_font_scale"), "user_settings", "bubble_font_scale BETWEEN 80 AND 160"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_user_settings_bubble_font_scale"), "user_settings", type_="check")
    op.drop_column("user_settings", "bubble_font_scale")
    op.drop_table("vocab_ai_notes")
    op.drop_index("ix_saved_sentences_user_id_created_at", table_name="saved_sentences")
    op.drop_table("saved_sentences")
