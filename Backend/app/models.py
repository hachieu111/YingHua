"""ORM ánh xạ đúng các bảng trong db/schema.sql (schema.sql là nguồn chuẩn, không dùng create_all)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, Numeric,
                        SmallInteger, String, Text, func, text)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

TS = DateTime(timezone=True)


def _pk():
    return mapped_column(BigInteger, primary_key=True)


def _created():
    return mapped_column(TS, server_default=func.now(), nullable=False)


# ------------------------------------------------------------------ users
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = _pk()
    email: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(16), server_default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = _created()
    last_login_at: Mapped[datetime | None] = mapped_column(TS)

    settings: Mapped["UserSettings"] = relationship(back_populates="user", uselist=False)


class UserSettings(Base):
    __tablename__ = "user_settings"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    hsk_level: Mapped[int] = mapped_column(SmallInteger, server_default="1")
    daily_new_cards: Mapped[int] = mapped_column(SmallInteger, server_default="10")
    daily_review_cap: Mapped[int] = mapped_column(SmallInteger, server_default="100")
    default_mode: Mapped[str] = mapped_column(String(8), server_default="read")
    show_pinyin: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    tts_voice: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship(back_populates="settings")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[int] = _pk()
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    expires_at: Mapped[datetime] = mapped_column(TS)
    revoked_at: Mapped[datetime | None] = mapped_column(TS)
    replaced_by: Mapped[int | None] = mapped_column(ForeignKey("refresh_tokens.id", ondelete="SET NULL"))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = _created()


# ------------------------------------------------------------------ files
class StoredFile(Base):
    __tablename__ = "stored_files"
    id: Mapped[int] = _pk()
    kind: Mapped[str] = mapped_column(String(16))
    storage_key: Mapped[str] = mapped_column(Text, unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    mime_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    expires_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = _created()


# ------------------------------------------------------------------ content
class Series(Base):
    __tablename__ = "series"
    id: Mapped[int] = _pk()
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    visibility: Mapped[str] = mapped_column(String(8), server_default="private")
    title_zh: Mapped[str | None] = mapped_column(String(255))
    title_vi: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    cover_file_id: Mapped[int | None] = mapped_column(ForeignKey("stored_files.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(12), server_default="ongoing")
    est_hsk_level: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = _created()


class Chapter(Base):
    __tablename__ = "chapters"
    id: Mapped[int] = _pk()
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id", ondelete="CASCADE"))
    number: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    title: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = _created()

    series: Mapped[Series] = relationship()


class Translation(Base):
    __tablename__ = "translations"
    id: Mapped[int] = _pk()
    source_file_id: Mapped[int | None] = mapped_column(ForeignKey("stored_files.id", ondelete="SET NULL"))
    phash: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(12), server_default="queued")
    pipeline_version: Mapped[str] = mapped_column(String(32))
    mode: Mapped[str | None] = mapped_column(String(32))
    inpainted_file_id: Mapped[int | None] = mapped_column(ForeignKey("stored_files.id", ondelete="SET NULL"))
    rendered_file_id: Mapped[int | None] = mapped_column(ForeignKey("stored_files.id", ondelete="SET NULL"))
    stats: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    error: Mapped[str | None] = mapped_column(Text)
    processing_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = _created()
    finished_at: Mapped[datetime | None] = mapped_column(TS)

    bubbles: Mapped[list["Bubble"]] = relationship(order_by="Bubble.idx", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"
    id: Mapped[int] = _pk()
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"))
    page_no: Mapped[int] = mapped_column(SmallInteger)
    original_file_id: Mapped[int | None] = mapped_column(ForeignKey("stored_files.id", ondelete="SET NULL"))
    translation_id: Mapped[int | None] = mapped_column(ForeignKey("translations.id", ondelete="SET NULL"))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = _created()

    chapter: Mapped[Chapter] = relationship()
    translation: Mapped[Translation | None] = relationship()
    original_file: Mapped[StoredFile | None] = relationship()


class Bubble(Base):
    __tablename__ = "bubbles"
    id: Mapped[int] = _pk()
    translation_id: Mapped[int] = mapped_column(ForeignKey("translations.id", ondelete="CASCADE"))
    idx: Mapped[int] = mapped_column(SmallInteger)
    class_name: Mapped[str] = mapped_column(String(16))
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    w: Mapped[int] = mapped_column(Integer)
    h: Mapped[int] = mapped_column(Integer)
    polygon: Mapped[list | None] = mapped_column(JSONB)
    confidence: Mapped[float | None] = mapped_column(Float)
    text_zh: Mapped[str] = mapped_column(Text)
    pinyin: Mapped[str | None] = mapped_column(Text)
    text_vi: Mapped[str | None] = mapped_column(Text)
    translate_method: Mapped[str | None] = mapped_column(String(32))
    lines: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    tokens: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    style: Mapped[dict | None] = mapped_column(JSONB)


class BubbleEdit(Base):
    __tablename__ = "bubble_edits"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    bubble_id: Mapped[int] = mapped_column(ForeignKey("bubbles.id", ondelete="CASCADE"), primary_key=True)
    text_vi: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())


class ReadingProgress(Base):
    __tablename__ = "reading_progress"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), primary_key=True)
    last_page_no: Mapped[int] = mapped_column(SmallInteger, server_default="1")
    mode: Mapped[str] = mapped_column(String(8), server_default="read")
    completed: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())


# ------------------------------------------------------------------ dictionaries
class DictEntry(Base):
    __tablename__ = "dict_entries"
    id: Mapped[int] = _pk()
    simplified: Mapped[str] = mapped_column(String(32))
    traditional: Mapped[str | None] = mapped_column(String(32))
    pinyin: Mapped[str] = mapped_column(String(128))
    pinyin_numeric: Mapped[str] = mapped_column(String(128))
    han_viet: Mapped[str | None] = mapped_column(String(128))
    meanings_vi: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    meanings_en: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    hsk_level: Mapped[int | None] = mapped_column(SmallInteger)
    freq_rank: Mapped[int | None] = mapped_column(Integer)
    pinyin_source: Mapped[str] = mapped_column(String(16), server_default="pypinyin")
    source: Mapped[str] = mapped_column(String(16))


class DictExample(Base):
    __tablename__ = "dict_examples"
    id: Mapped[int] = _pk()
    entry_id: Mapped[int] = mapped_column(ForeignKey("dict_entries.id", ondelete="CASCADE"))
    zh: Mapped[str] = mapped_column(Text)
    pinyin: Mapped[str | None] = mapped_column(Text)
    vi: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(16), server_default="curated")


class Hanzi(Base):
    __tablename__ = "hanzi"
    ch: Mapped[str] = mapped_column(String(2), primary_key=True)
    pinyin: Mapped[str | None] = mapped_column(String(64))
    pinyin_source: Mapped[str | None] = mapped_column(String(16))
    han_viet: Mapped[str | None] = mapped_column(String(64))
    radical: Mapped[str | None] = mapped_column(String(2))
    stroke_count: Mapped[int | None] = mapped_column(SmallInteger)
    decomposition: Mapped[str | None] = mapped_column(String(64))
    components: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    etymology: Mapped[dict | None] = mapped_column(JSONB)
    definition_en: Mapped[str | None] = mapped_column(Text)
    stroke_data: Mapped[dict | None] = mapped_column(JSONB)


class XianxiaEntry(Base):
    __tablename__ = "xianxia_entries"
    id: Mapped[int] = _pk()
    kind: Mapped[str] = mapped_column(String(8))
    key: Mapped[str] = mapped_column(String(32))
    pinyin: Mapped[str | None] = mapped_column(String(128))
    pinyin_numeric: Mapped[str | None] = mapped_column(String(128))
    meanings: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))


# ------------------------------------------------------------------ vocab & SRS
class UserVocab(Base):
    __tablename__ = "user_vocab"
    id: Mapped[int] = _pk()
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    term: Mapped[str] = mapped_column(String(32))
    entry_id: Mapped[int | None] = mapped_column(ForeignKey("dict_entries.id", ondelete="SET NULL"))
    custom_meaning: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), server_default="learning")
    source: Mapped[str] = mapped_column(String(12))
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())

    entry: Mapped[DictEntry | None] = relationship()
    contexts: Mapped[list["VocabContext"]] = relationship(order_by="VocabContext.id", cascade="all, delete-orphan")
    flashcards: Mapped[list["Flashcard"]] = relationship(order_by="Flashcard.id", cascade="all, delete-orphan",
                                                         back_populates="vocab")


class VocabContext(Base):
    __tablename__ = "vocab_contexts"
    id: Mapped[int] = _pk()
    user_vocab_id: Mapped[int] = mapped_column(ForeignKey("user_vocab.id", ondelete="CASCADE"))
    bubble_id: Mapped[int | None] = mapped_column(ForeignKey("bubbles.id", ondelete="SET NULL"))
    page_id: Mapped[int | None] = mapped_column(ForeignKey("pages.id", ondelete="SET NULL"))
    sentence_zh: Mapped[str] = mapped_column(Text)
    sentence_vi: Mapped[str | None] = mapped_column(Text)
    snippet_file_id: Mapped[int | None] = mapped_column(ForeignKey("stored_files.id", ondelete="SET NULL"))
    source_label: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = _created()


class Flashcard(Base):
    __tablename__ = "flashcards"
    id: Mapped[int] = _pk()
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user_vocab_id: Mapped[int] = mapped_column(ForeignKey("user_vocab.id", ondelete="CASCADE"))
    card_type: Mapped[str] = mapped_column(String(12), server_default="recognition")
    state: Mapped[str] = mapped_column(String(12), server_default="new")
    due_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    interval_days: Mapped[float] = mapped_column(Float, server_default="0")
    ease_factor: Mapped[float] = mapped_column(Float, server_default="2.5")
    stability: Mapped[float | None] = mapped_column(Float)
    difficulty: Mapped[float | None] = mapped_column(Float)
    reps: Mapped[int] = mapped_column(Integer, server_default="0")
    lapses: Mapped[int] = mapped_column(Integer, server_default="0")
    last_reviewed_at: Mapped[datetime | None] = mapped_column(TS)
    suspended: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = _created()

    vocab: Mapped[UserVocab] = relationship(back_populates="flashcards")


class ReviewLog(Base):
    __tablename__ = "review_logs"
    id: Mapped[int] = _pk()
    card_id: Mapped[int] = mapped_column(ForeignKey("flashcards.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    rating: Mapped[int] = mapped_column(SmallInteger)
    state_before: Mapped[str] = mapped_column(String(12))
    interval_before: Mapped[float] = mapped_column(Float)
    interval_after: Mapped[float] = mapped_column(Float)
    ease_after: Mapped[float | None] = mapped_column(Float)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    reviewed_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


# ------------------------------------------------------------------ personalisation
class LookupEvent(Base):
    __tablename__ = "lookup_events"
    id: Mapped[int] = _pk()
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    term: Mapped[str] = mapped_column(String(32))
    entry_id: Mapped[int | None] = mapped_column(ForeignKey("dict_entries.id", ondelete="SET NULL"))
    bubble_id: Mapped[int | None] = mapped_column(ForeignKey("bubbles.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(12))
    created_at: Mapped[datetime] = _created()


class ChapterVocab(Base):
    __tablename__ = "chapter_vocab"
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), primary_key=True)
    term: Mapped[str] = mapped_column(String(32), primary_key=True)
    entry_id: Mapped[int | None] = mapped_column(ForeignKey("dict_entries.id", ondelete="SET NULL"))
    occurrences: Mapped[int] = mapped_column(Integer)
    first_bubble_id: Mapped[int | None] = mapped_column(ForeignKey("bubbles.id", ondelete="SET NULL"))


class VocabSuggestion(Base):
    __tablename__ = "vocab_suggestions"
    id: Mapped[int] = _pk()
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"))
    term: Mapped[str] = mapped_column(String(32))
    entry_id: Mapped[int | None] = mapped_column(ForeignKey("dict_entries.id", ondelete="SET NULL"))
    score: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(12), server_default="pending")
    created_at: Mapped[datetime] = _created()


class TtsCache(Base):
    __tablename__ = "tts_cache"
    id: Mapped[int] = _pk()
    text_sha256: Mapped[str] = mapped_column(String(64))
    voice: Mapped[str] = mapped_column(String(64))
    file_id: Mapped[int] = mapped_column(ForeignKey("stored_files.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = _created()
