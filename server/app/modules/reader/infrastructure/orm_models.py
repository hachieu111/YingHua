"""Bảng của M05 (docs/database-design.md §4.8). Tạo ở migration 0005; mã nghiệp vụ làm ở lượt 3b."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
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
