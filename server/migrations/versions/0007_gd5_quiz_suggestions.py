"""Giai đoạn 5: M09 bài kiểm tra (quizzes, quiz_questions) và M10 gợi ý (dismissed_suggestions).

Gồm cả mở rộng F09.09 (từ mở rộng + câu ví dụ): cột `target_kind`, `term`, `related_entry_id`, `example_id`,
`example_form`, `hint` của quiz_questions; `related_score`, `related_count` của quizzes; và
`dict_examples.difficulty_level` (chỉ thêm cột, KHÔNG tính ở đây: dùng scripts/compute_example_difficulty.py).

Không tạo bảng `chapter_vocab`: danh sách gợi ý được tính khi yêu cầu từ `bubbles.tokens` của các trang
trong chương (SRS: "tính khi yêu cầu, không lưu sẵn"). `dismissed_suggestions` khóa theo (user_id, term) vì
quy tắc F10.03: đã bỏ qua thì không gợi ý lại ở mọi chương.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quizzes",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=12), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("question_count", sa.SmallInteger(), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=True),
        sa.Column("wrong_cards_rescheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fallback_reason", sa.String(length=24), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("related_score", sa.SmallInteger(), nullable=True),
        sa.Column("related_count", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("source IN ('llm', 'fallback', 'mixed')", name=op.f("ck_quizzes_source")),
        sa.CheckConstraint("status IN ('in_progress', 'submitted')", name=op.f("ck_quizzes_status")),
        sa.CheckConstraint(
            "fallback_reason IN ('llm_disabled', 'timeout', 'invalid_schema', 'network', 'daily_limit')",
            name=op.f("ck_quizzes_fallback_reason"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_quizzes_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quizzes")),
    )
    op.create_index("ix_quizzes_user_id_created_at", "quizzes", ["user_id", "created_at"], unique=False)
    op.create_table(
        "quiz_questions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("quiz_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("question_type", sa.String(length=16), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column(
            "accepted_answers",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("vocab_entry_id", sa.BigInteger(), nullable=True),
        sa.Column("origin", sa.String(length=12), nullable=False),
        sa.Column("user_answer", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("term", sa.String(length=32), nullable=False),
        sa.Column("target_kind", sa.String(length=8), server_default="saved", nullable=False),
        sa.Column("related_entry_id", sa.BigInteger(), nullable=True),
        sa.Column("example_id", sa.BigInteger(), nullable=True),
        sa.Column("example_form", sa.String(length=10), nullable=True),
        sa.Column("hint", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "question_type IN ('multiple_choice', 'fill_blank')", name=op.f("ck_quiz_questions_question_type")
        ),
        sa.CheckConstraint("origin IN ('llm', 'fallback')", name=op.f("ck_quiz_questions_origin")),
        sa.CheckConstraint(
            "target_kind IN ('saved', 'related')", name=op.f("ck_quiz_questions_target_kind")
        ),
        sa.CheckConstraint(
            "example_form IN ('cloze', 'sense', 'translate')", name=op.f("ck_quiz_questions_example_form")
        ),
        sa.ForeignKeyConstraint(
            ["quiz_id"], ["quizzes.id"], name=op.f("fk_quiz_questions_quiz_id_quizzes"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["vocab_entry_id"],
            ["vocab_entries.id"],
            name=op.f("fk_quiz_questions_vocab_entry_id_vocab_entries"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["related_entry_id"],
            ["vocab_entries.id"],
            name=op.f("fk_quiz_questions_related_entry_id_vocab_entries"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["example_id"],
            ["dict_examples.id"],
            name=op.f("fk_quiz_questions_example_id_dict_examples"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quiz_questions")),
        sa.UniqueConstraint("quiz_id", "position", name=op.f("uq_quiz_questions_quiz_id_position")),
    )
    op.create_index("ix_quiz_questions_example_id", "quiz_questions", ["example_id"], unique=False)
    op.add_column("dict_examples", sa.Column("difficulty_level", sa.SmallInteger(), nullable=True))
    op.create_index(
        "ix_dict_examples_difficulty_level",
        "dict_examples",
        ["difficulty_level"],
        unique=False,
        postgresql_where=sa.text("source = 'tatoeba' AND vi IS NOT NULL"),
    )
    op.create_table(
        "dismissed_suggestions",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("term", sa.String(length=32), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_dismissed_suggestions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "term", name=op.f("pk_dismissed_suggestions")),
    )


def downgrade() -> None:
    op.drop_table("dismissed_suggestions")
    op.drop_index(
        "ix_dict_examples_difficulty_level",
        table_name="dict_examples",
        postgresql_where=sa.text("source = 'tatoeba' AND vi IS NOT NULL"),
    )
    op.drop_column("dict_examples", "difficulty_level")
    op.drop_index("ix_quiz_questions_example_id", table_name="quiz_questions")
    op.drop_table("quiz_questions")
    op.drop_index("ix_quizzes_user_id_created_at", table_name="quizzes")
    op.drop_table("quizzes")
