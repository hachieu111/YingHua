"""Bảng của M06 Từ điển (docs/database-design.md §4.4). Chỉ dùng trong tầng hạ tầng."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
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
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

TS = DateTime(timezone=True)


class DictEntryModel(Base):
    __tablename__ = "dict_entries"
    __table_args__ = (
        UniqueConstraint("simplified", "pinyin_numeric", "source"),
        CheckConstraint("pinyin_source IN ('dict', 'pypinyin')", name="pinyin_source"),
        Index("ix_dict_entries_simplified", "simplified"),
        Index("ix_dict_entries_traditional", "traditional"),
        Index(
            "ix_dict_entries_pinyin_search",
            "pinyin_search",
            postgresql_ops={"pinyin_search": "varchar_pattern_ops"},
        ),
        Index(
            "ix_dict_entries_search_vi_trgm",
            "search_vi",
            postgresql_using="gin",
            postgresql_ops={"search_vi": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    simplified: Mapped[str] = mapped_column(String(64))
    traditional: Mapped[str | None] = mapped_column(String(64))
    pinyin: Mapped[str] = mapped_column(String(160))  # có dấu thanh
    pinyin_numeric: Mapped[str] = mapped_column(String(160))  # xue2 xi2
    pinyin_search: Mapped[str] = mapped_column(String(128))  # xuexi — khóa tìm kiếm không dấu
    pinyin_source: Mapped[str] = mapped_column(String(16), server_default="dict")
    han_viet: Mapped[str | None] = mapped_column(String(160))
    meanings_vi: Mapped[list[dict[str, str]]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    meanings_en: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    search_vi: Mapped[str] = mapped_column(Text, server_default="")  # nghĩa Việt gộp, chữ thường
    part_of_speech: Mapped[str | None] = mapped_column(String(64))  # mã gốc, vd "v,vn"
    freq_rank: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(16))


class DictExampleModel(Base):
    __tablename__ = "dict_examples"
    __table_args__ = (
        CheckConstraint("source IN ('curated', 'gloss', 'tatoeba', 'llm')", name="source"),
        Index("ix_dict_examples_entry_id", "entry_id"),
        Index(
            "ix_dict_examples_difficulty_level",
            "difficulty_level",
            postgresql_where=text("source = 'tatoeba' AND vi IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    entry_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dict_entries.id", ondelete="CASCADE"))
    zh: Mapped[str] = mapped_column(Text)
    pinyin: Mapped[str | None] = mapped_column(Text)
    vi: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(16), server_default="gloss")
    source_ref: Mapped[str | None] = mapped_column(
        String(32)
    )  # vd. mã câu Tatoeba để ghi nguồn (CC BY 2.0 FR)
    # Cấp HSK cao nhất của các từ trong câu (script compute_example_difficulty.py); NULL = chưa tính.
    difficulty_level: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class HanziModel(Base):
    __tablename__ = "hanzi"

    ch: Mapped[str] = mapped_column(String(2), primary_key=True)
    pinyin: Mapped[str | None] = mapped_column(String(64))
    pinyin_source: Mapped[str | None] = mapped_column(String(16))
    han_viet: Mapped[str | None] = mapped_column(String(64))
    radical: Mapped[str | None] = mapped_column(String(2))
    stroke_count: Mapped[int | None] = mapped_column(SmallInteger)
    decomposition: Mapped[str | None] = mapped_column(String(64))
    components: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    etymology: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    definition_en: Mapped[str | None] = mapped_column(Text)
    stroke_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class XianxiaEntryModel(Base):
    __tablename__ = "xianxia_entries"
    __table_args__ = (
        CheckConstraint("kind IN ('phrase', 'name', 'char')", name="kind"),
        Index("ix_xianxia_entries_kind_key", "kind", "key"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    kind: Mapped[str] = mapped_column(String(8))
    key: Mapped[str] = mapped_column(String(64))
    pinyin: Mapped[str | None] = mapped_column(String(160))
    pinyin_numeric: Mapped[str | None] = mapped_column(String(160))
    meanings: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))


class XianxiaRuleModel(Base):
    __tablename__ = "xianxia_rules"

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    rule: Mapped[str] = mapped_column(Text)


class HskWordModel(Base):
    __tablename__ = "hsk_words"
    __table_args__ = (
        CheckConstraint("level BETWEEN 1 AND 9", name="level"),
        Index("ix_hsk_words_level", "level"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    word: Mapped[str] = mapped_column(String(32), unique=True)
    level: Mapped[int] = mapped_column(SmallInteger)  # 7 đại diện nhóm 7–9 của HSK 3.0
    pinyin: Mapped[str | None] = mapped_column(String(128))
    pos: Mapped[str | None] = mapped_column(String(64))
    list_version: Mapped[str] = mapped_column(String(16), server_default="3.0")
    imported_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class LookupEventModel(Base):
    __tablename__ = "lookup_events"
    __table_args__ = (
        CheckConstraint("action IN ('hover', 'lookup', 'decompose', 'tts')", name="action"),
        Index("ix_lookup_events_user_id_term", "user_id", "term"),
        Index("ix_lookup_events_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    term: Mapped[str] = mapped_column(String(64))
    entry_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("dict_entries.id", ondelete="SET NULL")
    )
    bubble_id: Mapped[int | None] = mapped_column(BigInteger)  # khóa ngoại tới bubbles thêm ở Giai đoạn 3
    action: Mapped[str] = mapped_column(String(12))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
