"""Bảng của M16 (docs/database-design.md §4.18). Tạo ở migration 0012. Chỉ dùng trong tầng hạ tầng."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

TS = DateTime(timezone=True)


class XpEventModel(Base):
    __tablename__ = "xp_events"
    __table_args__ = (
        CheckConstraint(
            "source IN ('page_read', 'review', 'word_saved', 'quiz', 'minigame', 'quest', 'weekly_goal',"
            " 'streak_milestone')",
            name="source",
        ),
        CheckConstraint("amount BETWEEN 0 AND 1000", name="amount"),
        UniqueConstraint("user_id", "source", "source_ref"),
        Index("ix_xp_events_created_at_user_id", "created_at", "user_id"),
        Index("ix_xp_events_user_id_activity_date", "user_id", "activity_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(20))
    source_ref: Mapped[str] = mapped_column(String(64))
    amount: Mapped[int] = mapped_column(SmallInteger)
    capped: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    activity_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class SeasonModel(Base):
    __tablename__ = "seasons"
    __table_args__ = (
        CheckConstraint("number >= 1", name="number"),
        CheckConstraint("ends_at > starts_at", name="period"),
        CheckConstraint("status IN ('active', 'finalizing', 'finalized')", name="status"),
        Index("ix_seasons_status_ends_at", "status", "ends_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True)
    starts_at: Mapped[datetime] = mapped_column(TS, unique=True)
    ends_at: Mapped[datetime] = mapped_column(TS)
    status: Mapped[str] = mapped_column(String(12), server_default="active")
    finalized_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class SeasonResultModel(Base):
    __tablename__ = "season_results"
    __table_args__ = (
        CheckConstraint("rank BETWEEN 1 AND 50", name="rank"),
        CheckConstraint("xp >= 0", name="xp"),
        CheckConstraint("tier IN ('top3', 'top10', 'top50')", name="tier"),
        UniqueConstraint("season_id", "rank"),
        Index("ix_season_results_user_id", "user_id"),
    )

    season_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("seasons.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    rank: Mapped[int] = mapped_column(SmallInteger)
    xp: Mapped[int] = mapped_column(Integer)
    tier: Mapped[str] = mapped_column(String(8))
    reward_granted_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class AchievementModel(Base):
    __tablename__ = "achievements"
    __table_args__ = (
        CheckConstraint(
            "metric IN ('study_days', 'pages_read', 'words_saved', 'hsk3_mastered', 'night_pages',"
            " 'bubble_lookups', 'season_top3')",
            name="metric",
        ),
        CheckConstraint("cardinality(thresholds) BETWEEN 1 AND 3", name="thresholds"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(255))
    metric: Mapped[str] = mapped_column(String(24))
    thresholds: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    coin_rewards: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    style_key: Mapped[str] = mapped_column(String(32))
    sort_order: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())


class UserAchievementModel(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (
        CheckConstraint("tier BETWEEN 1 AND 3", name="tier"),
        CheckConstraint("source IN ('rule', 'season')", name="source"),
        Index(
            "uq_user_achievements_user_id_equipped",
            "user_id",
            unique=True,
            postgresql_where=text("is_equipped"),
        ),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    achievement_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("achievements.id", ondelete="RESTRICT"), primary_key=True
    )
    tier: Mapped[int] = mapped_column(SmallInteger)
    source: Mapped[str] = mapped_column(String(8))
    is_equipped: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    unlocked_at: Mapped[datetime] = mapped_column(TS)
    tier_reached_at: Mapped[datetime] = mapped_column(TS)


class MinigameRoundModel(Base):
    __tablename__ = "minigame_rounds"
    __table_args__ = (
        CheckConstraint("mode IN ('hsk', 'weak_radical')", name="mode"),
        CheckConstraint("hsk_band BETWEEN 1 AND 7", name="hsk_band"),
        Index("ix_minigame_rounds_user_id_issued_at", "user_id", "issued_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    mode: Mapped[str] = mapped_column(String(16))
    hsk_band: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    radical: Mapped[str | None] = mapped_column(String(8), nullable=True)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    issued_at: Mapped[datetime] = mapped_column(TS)
    submitted_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class MinigameSessionModel(Base):
    __tablename__ = "minigame_sessions"
    __table_args__ = (
        CheckConstraint("game_type IN ('falling_radical', 'pinyin_blade')", name="game_type"),
        CheckConstraint("hsk_band BETWEEN 1 AND 7", name="hsk_band"),
        Index("ix_minigame_sessions_user_id_played_at", "user_id", "played_at"),
        Index("ix_minigame_sessions_user_id_game_type_hsk_band", "user_id", "game_type", "hsk_band"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    game_type: Mapped[str] = mapped_column(String(24))
    target_radical: Mapped[str | None] = mapped_column(String(8), nullable=True)
    hsk_band: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    score: Mapped[int] = mapped_column(SmallInteger)
    correct: Mapped[int] = mapped_column(SmallInteger)
    wrong: Mapped[int] = mapped_column(SmallInteger)
    typos: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    max_combo: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    duration_ms: Mapped[int] = mapped_column(Integer)
    played_at: Mapped[datetime] = mapped_column(TS)
