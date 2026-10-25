"""Bảng của M08 (docs/database-design.md §4.11). Tạo ở migration 0006."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

TS = DateTime(timezone=True)


class CardModel(Base):
    __tablename__ = "cards"
    __table_args__ = (
        CheckConstraint("card_type IN ('recognition', 'recall', 'listening')", name="card_type"),
        CheckConstraint("state IN ('learning', 'review', 'relearning')", name="state"),
        UniqueConstraint("vocab_entry_id", "card_type"),
        Index("ix_cards_user_id_due_at", "user_id", "due_at", postgresql_where=text("NOT is_suspended")),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    vocab_entry_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vocab_entries.id", ondelete="CASCADE")
    )
    card_type: Mapped[str] = mapped_column(String(12))
    state: Mapped[str] = mapped_column(String(12))
    step: Mapped[int | None] = mapped_column(SmallInteger)
    stability: Mapped[float | None] = mapped_column(Double)
    difficulty: Mapped[float | None] = mapped_column(Double)
    due_at: Mapped[datetime] = mapped_column(TS)
    last_review_at: Mapped[datetime | None] = mapped_column(TS)
    reps: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    lapses: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    is_suspended: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())


class ReviewLogModel(Base):
    __tablename__ = "review_logs"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 4", name="rating"),
        UniqueConstraint("presentation_id"),
        Index("ix_review_logs_card_id", "card_id"),
        Index("ix_review_logs_user_id_reviewed_at", "user_id", "reviewed_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    card_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cards.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    rating: Mapped[int] = mapped_column(SmallInteger)
    state_before: Mapped[str] = mapped_column(String(12))
    stability_before: Mapped[float | None] = mapped_column(Double)
    stability_after: Mapped[float | None] = mapped_column(Double)
    difficulty_before: Mapped[float | None] = mapped_column(Double)
    difficulty_after: Mapped[float | None] = mapped_column(Double)
    due_after: Mapped[datetime] = mapped_column(TS)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    presentation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    reviewed_at: Mapped[datetime] = mapped_column(TS)


class FsrsParametersModel(Base):
    """Tham số FSRS riêng từng người (F08.08, GĐ6). Bảng tạo sẵn; GĐ4 dùng tham số mặc định của thư viện."""

    __tablename__ = "fsrs_parameters"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    weights: Mapped[list[float]] = mapped_column(ARRAY(Double))
    desired_retention: Mapped[Decimal] = mapped_column(Numeric(3, 2), server_default=text("0.90"))
    review_count: Mapped[int] = mapped_column(Integer)
    optimized_at: Mapped[datetime] = mapped_column(TS)


class VocabAiNoteModel(Base):
    """Bộ đệm Thẻ mở rộng AI của mục từ (F08.11); xóa mục từ thì xóa theo (migration 0008)."""

    __tablename__ = "vocab_ai_notes"
    __table_args__ = (CheckConstraint("source IN ('llm', 'fallback')", name="source"),)

    vocab_entry_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vocab_entries.id", ondelete="CASCADE"), primary_key=True
    )
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    model: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(12))
    generated_at: Mapped[datetime] = mapped_column(TS)
    regenerate_count: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
