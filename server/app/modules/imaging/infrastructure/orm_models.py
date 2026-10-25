"""Bảng `translations` và `bubbles` (docs/database-design.md §4.7). Chỉ dùng trong tầng hạ tầng."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
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
from app.core.stored_files import StoredFileModel  # noqa: F401  (đăng ký bảng cho khóa ngoại)

TS = DateTime(timezone=True)


class TranslationModel(Base):
    __tablename__ = "translations"
    __table_args__ = (
        CheckConstraint("status IN ('queued', 'running', 'done', 'failed')", name="status"),
        Index("ix_translations_sha256", "sha256"),
        Index("ix_translations_phash", "phash"),
        Index("ix_translations_status_queued_at", "status", "queued_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    source_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("stored_files.id", ondelete="SET NULL")
    )
    sha256: Mapped[str] = mapped_column(CHAR(64))
    phash: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(12), server_default="queued")
    pipeline_version: Mapped[str] = mapped_column(String(32))
    attempts: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    worker_id: Mapped[str | None] = mapped_column(String(64))
    error_step: Mapped[str | None] = mapped_column(String(32))
    error_message: Mapped[str | None] = mapped_column(String(1000))
    inpainted_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("stored_files.id", ondelete="SET NULL")
    )
    rendered_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("stored_files.id", ondelete="SET NULL")
    )
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    processing_ms: Mapped[int | None] = mapped_column(Integer)
    queued_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(TS)
    finished_at: Mapped[datetime | None] = mapped_column(TS)


class BubbleModel(Base):
    __tablename__ = "bubbles"
    __table_args__ = (
        CheckConstraint(
            "class_name IN ('speech_bubble', 'sound_effect', 'calligraphy', 'floating_text')",
            name="class_name",
        ),
        UniqueConstraint("translation_id", "idx"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    translation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("translations.id", ondelete="CASCADE"))
    idx: Mapped[int] = mapped_column(SmallInteger)
    class_name: Mapped[str] = mapped_column(String(16))
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    w: Mapped[int] = mapped_column(Integer)
    h: Mapped[int] = mapped_column(Integer)
    polygon: Mapped[Any | None] = mapped_column(JSONB)
    confidence: Mapped[float | None] = mapped_column(Float)
    text_zh: Mapped[str] = mapped_column(Text)
    pinyin: Mapped[str | None] = mapped_column(Text)
    text_vi: Mapped[str | None] = mapped_column(Text)
    translate_method: Mapped[str | None] = mapped_column(String(32))
    lines: Mapped[list[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    tokens: Mapped[list[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    style: Mapped[Any | None] = mapped_column(JSONB)
