"""Bảng của M09 (docs/database-design.md §4.13). Tạo ở migration 0007."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

TS = DateTime(timezone=True)


class QuizModel(Base):
    __tablename__ = "quizzes"
    __table_args__ = (
        CheckConstraint("source IN ('llm', 'fallback', 'mixed')", name="source"),
        CheckConstraint("status IN ('in_progress', 'submitted')", name="status"),
        CheckConstraint(
            "fallback_reason IN ('llm_disabled', 'timeout', 'invalid_schema', 'network', 'daily_limit')",
            name="fallback_reason",
        ),
        Index("ix_quizzes_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(String(12))
    question_count: Mapped[int] = mapped_column(SmallInteger)
    score: Mapped[int | None] = mapped_column(SmallInteger)
    wrong_cards_rescheduled_at: Mapped[datetime | None] = mapped_column(TS)
    fallback_reason: Mapped[str | None] = mapped_column(String(24))
    note: Mapped[str | None] = mapped_column(Text)
    related_score: Mapped[int | None] = mapped_column(SmallInteger)
    related_count: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(TS)


class QuizQuestionModel(Base):
    __tablename__ = "quiz_questions"
    __table_args__ = (
        CheckConstraint("question_type IN ('multiple_choice', 'fill_blank')", name="question_type"),
        CheckConstraint("origin IN ('llm', 'fallback')", name="origin"),
        CheckConstraint("target_kind IN ('saved', 'related')", name="target_kind"),
        CheckConstraint("example_form IN ('cloze', 'sense', 'translate')", name="example_form"),
        Index("ix_quiz_questions_example_id", "example_id"),
        UniqueConstraint("quiz_id", "position"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    quiz_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("quizzes.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(SmallInteger)
    question_type: Mapped[str] = mapped_column(String(16))
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str] | None] = mapped_column(JSONB)
    correct_answer: Mapped[str] = mapped_column(Text)
    accepted_answers: Mapped[list[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    explanation: Mapped[str | None] = mapped_column(Text)
    vocab_entry_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("vocab_entries.id", ondelete="SET NULL")
    )
    origin: Mapped[str] = mapped_column(String(12))
    user_answer: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    term: Mapped[str] = mapped_column(String(32))
    target_kind: Mapped[str] = mapped_column(String(8), server_default="saved")
    related_entry_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("vocab_entries.id", ondelete="SET NULL")
    )
    example_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("dict_examples.id", ondelete="SET NULL")
    )
    example_form: Mapped[str | None] = mapped_column(String(10))
    hint: Mapped[str | None] = mapped_column(Text)
