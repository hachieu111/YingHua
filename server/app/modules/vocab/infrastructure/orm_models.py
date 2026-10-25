"""Bảng của M07 (docs/database-design.md §4.10, §6.2). Tạo ở migration 0006."""

from __future__ import annotations

from datetime import datetime

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
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

TS = DateTime(timezone=True)


class VocabEntryModel(Base):
    __tablename__ = "vocab_entries"
    __table_args__ = (
        CheckConstraint("hsk_level BETWEEN 1 AND 9", name="hsk_level"),
        CheckConstraint("hsk_source IN ('list', 'derived', 'none')", name="hsk_source"),
        CheckConstraint("status IN ('learning', 'known', 'ignored')", name="status"),
        CheckConstraint("source IN ('highlight', 'lookup', 'suggestion', 'manual', 'quiz')", name="source"),
        UniqueConstraint("user_id", "term"),
        Index("ix_vocab_entries_user_id_status", "user_id", "status"),
        Index("ix_vocab_entries_user_id_hsk_level", "user_id", "hsk_level"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    term: Mapped[str] = mapped_column(String(32))
    entry_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("dict_entries.id", ondelete="SET NULL")
    )
    pinyin: Mapped[str | None] = mapped_column(String(128))
    meaning_vi: Mapped[str | None] = mapped_column(Text)
    hsk_level: Mapped[int | None] = mapped_column(SmallInteger)
    hsk_source: Mapped[str] = mapped_column(String(12), server_default="none")
    status: Mapped[str] = mapped_column(String(12), server_default="learning")
    source: Mapped[str] = mapped_column(String(12))
    note: Mapped[str | None] = mapped_column(String(1000))
    is_starred: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())


class VocabContextModel(Base):
    __tablename__ = "vocab_contexts"
    __table_args__ = (
        UniqueConstraint("vocab_entry_id", "bubble_id"),
        Index("ix_vocab_contexts_vocab_entry_id", "vocab_entry_id"),
        Index("ix_vocab_contexts_page_id", "page_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    vocab_entry_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vocab_entries.id", ondelete="CASCADE")
    )
    bubble_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("bubbles.id", ondelete="SET NULL"))
    page_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("pages.id", ondelete="SET NULL"))
    sentence_zh: Mapped[str] = mapped_column(Text)
    sentence_vi: Mapped[str | None] = mapped_column(Text)
    # Ảnh cắt là bản sao độc lập (kind "snippet", không hết hạn): xóa trang/truyện không làm mất ảnh này.
    snippet_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("stored_files.id", ondelete="SET NULL")
    )
    source_label: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class SavedSentenceModel(Base):
    """Câu thoại đã lưu (F07.11); lưu bản sao văn bản nên giữ nguyên khi bong bóng/trang bị xóa."""

    __tablename__ = "saved_sentences"
    __table_args__ = (
        UniqueConstraint("user_id", "bubble_id"),
        Index("ix_saved_sentences_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    bubble_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("bubbles.id", ondelete="SET NULL"))
    page_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("pages.id", ondelete="SET NULL"))
    sentence_zh: Mapped[str] = mapped_column(Text)
    sentence_vi: Mapped[str | None] = mapped_column(Text)
    source_label: Mapped[str | None] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())
