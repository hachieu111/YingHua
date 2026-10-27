"""Bảng của M05 (docs/database-design.md §4.8). Tạo ở migration 0005; mã nghiệp vụ làm ở lượt 3b."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

TS = DateTime(timezone=True)


class BubbleEditModel(Base):
    __tablename__ = "bubble_edits"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    bubble_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("bubbles.id", ondelete="CASCADE"), primary_key=True
    )
    text_vi: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())


class GuestSessionModel(Base):
    __tablename__ = "guest_sessions"
    __table_args__ = (Index("ix_guest_sessions_expires_at", "expires_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    lookup_count: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(TS)


class GrammarAnalysisModel(Base):
    """Kết quả phân tích ngữ pháp dùng chung mọi người (F05.09, migration 0011)."""

    __tablename__ = "grammar_analyses"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    sentence_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    sentence_zh: Mapped[str] = mapped_column(Text)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    model: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class GrammarRequestModel(Base):
    """Mỗi lượt người học phải gọi LLM, để đếm hạn mức ngày (F05.09, migration 0011)."""

    __tablename__ = "grammar_requests"
    __table_args__ = (Index("ix_grammar_requests_user_id_requested_at", "user_id", "requested_at"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    analysis_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("grammar_analyses.id", ondelete="SET NULL")
    )
    requested_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class PageAnnotationModel(Base):
    __tablename__ = "page_annotations"
    __table_args__ = (Index("ix_page_annotations_user_id_updated_at", "user_id", "updated_at"),)

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    page_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("pages.id", ondelete="CASCADE"), primary_key=True
    )
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    highlights: Mapped[list[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    strokes: Mapped[list[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())
