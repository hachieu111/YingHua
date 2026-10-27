"""Giai đoạn 6 (nhóm AI): phân tích ngữ pháp câu thoại và "Vì sao sai?" trong kết quả kiểm tra.

- `grammar_analyses` (F05.09, US-NH-78): kết quả phân tích dùng chung mọi người, cache theo SHA-256 của câu.
- `grammar_requests` (F05.09): mỗi lượt phải gọi LLM của một người, để đếm hạn mức theo ngày.
- `quiz_questions.mistake_review`, `mistake_review_at` (F09.10, US-NH-79): giải thích lỗi sai
  và câu luyện thêm.

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "grammar_analyses",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("sentence_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("sentence_zh", sa.Text(), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grammar_analyses")),
        sa.UniqueConstraint("sentence_hash", name=op.f("uq_grammar_analyses_sentence_hash")),
    )
    op.create_table(
        "grammar_requests",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("analysis_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_grammar_requests_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["grammar_analyses.id"],
            name=op.f("fk_grammar_requests_analysis_id_grammar_analyses"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grammar_requests")),
    )
    op.create_index(
        "ix_grammar_requests_user_id_requested_at", "grammar_requests", ["user_id", "requested_at"]
    )
    op.add_column(
        "quiz_questions", sa.Column("mistake_review", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.add_column("quiz_questions", sa.Column("mistake_review_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("quiz_questions", "mistake_review_at")
    op.drop_column("quiz_questions", "mistake_review")
    op.drop_index("ix_grammar_requests_user_id_requested_at", table_name="grammar_requests")
    op.drop_table("grammar_requests")
    op.drop_table("grammar_analyses")
