"""Bảng của M03 (docs/database-design.md §4.6). Chỉ dùng trong tầng hạ tầng."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.stored_files import StoredFileModel  # noqa: F401  (đăng ký bảng cho khóa ngoại)

TS = DateTime(timezone=True)


class SeriesModel(Base):
    __tablename__ = "series"
    __table_args__ = (
        CheckConstraint("visibility IN ('public', 'private')", name="visibility"),
        CheckConstraint("status IN ('ongoing', 'completed')", name="status"),
        CheckConstraint("est_hsk_level BETWEEN 1 AND 9", name="est_hsk_level"),
        CheckConstraint(
            "(visibility = 'public' AND owner_id IS NULL) "
            "OR (visibility = 'private' AND owner_id IS NOT NULL)",
            name="visibility_owner",
        ),
        Index("ix_series_owner_id", "owner_id"),
        Index("ix_series_visibility", "visibility"),
        Index(
            "ix_series_title_vi_trgm",
            "title_vi",
            postgresql_using="gin",
            postgresql_ops={"title_vi": "gin_trgm_ops"},
        ),
        Index(
            "ix_series_title_zh_trgm",
            "title_zh",
            postgresql_using="gin",
            postgresql_ops={"title_zh": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    visibility: Mapped[str] = mapped_column(String(8))
    title_vi: Mapped[str] = mapped_column(String(255))
    title_zh: Mapped[str | None] = mapped_column(String(255))
    author: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    cover_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("stored_files.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(12), server_default="ongoing")
    est_hsk_level: Mapped[int | None] = mapped_column(SmallInteger)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    genres: Mapped[list[str]] = mapped_column(ARRAY(String(32)), server_default=text("'{}'"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())


class ChapterModel(Base):
    __tablename__ = "chapters"
    __table_args__ = (
        UniqueConstraint("series_id", "number"),
        CheckConstraint("number >= 0", name="number"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    series_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("series.id", ondelete="CASCADE"))
    number: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    title: Mapped[str | None] = mapped_column(String(255))
    is_trial: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())


class PageModel(Base):
    __tablename__ = "pages"
    __table_args__ = (
        UniqueConstraint("chapter_id", "page_no"),
        CheckConstraint("chapter_id IS NOT NULL OR owner_id IS NOT NULL", name="chapter_or_owner"),
        Index("ix_pages_translation_id", "translation_id"),
        Index("ix_pages_owner_id", "owner_id"),
        Index("ix_pages_original_file_id", "original_file_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    chapter_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("chapters.id", ondelete="CASCADE"))
    owner_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    page_no: Mapped[int] = mapped_column(SmallInteger)
    original_file_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("stored_files.id", ondelete="SET NULL")
    )
    translation_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("translations.id", ondelete="SET NULL")
    )
    width: Mapped[int | None] = mapped_column()
    height: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class ReadingProgressModel(Base):
    __tablename__ = "reading_progress"
    __table_args__ = (
        CheckConstraint("mode IN ('read', 'learn')", name="mode"),
        Index("ix_reading_progress_user_id_updated_at", "user_id", "updated_at"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    chapter_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chapters.id", ondelete="CASCADE"), primary_key=True
    )
    last_page_no: Mapped[int] = mapped_column(SmallInteger)
    mode: Mapped[str] = mapped_column(String(8), server_default="read")
    completed: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class PageReadModel(Base):
    __tablename__ = "page_reads"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    page_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("pages.id", ondelete="CASCADE"), primary_key=True
    )
    first_read_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class LibraryItemModel(Base):
    __tablename__ = "library_items"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    series_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("series.id", ondelete="CASCADE"), primary_key=True
    )
    is_favorite: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    added_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class SeriesRatingModel(Base):
    __tablename__ = "series_ratings"
    __table_args__ = (
        CheckConstraint("stars BETWEEN 1 AND 5", name="stars"),
        Index("ix_series_ratings_series_id", "series_id"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    series_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("series.id", ondelete="CASCADE"), primary_key=True
    )
    stars: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())
