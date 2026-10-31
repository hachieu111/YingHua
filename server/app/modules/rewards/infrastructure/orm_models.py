"""Bảng của M17 (docs/database-design.md §4.19). Chỉ dùng trong tầng hạ tầng."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

TS = DateTime(timezone=True)


class AvatarFrameModel(Base):
    __tablename__ = "avatar_frames"
    __table_args__ = (CheckConstraint("acquire_kind IN ('season', 'shop', 'vip')", name="acquire_kind"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(String(255))
    style_key: Mapped[str] = mapped_column(String(32))
    acquire_kind: Mapped[str] = mapped_column(String(8))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class WalletModel(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        CheckConstraint("coin_balance >= 0", name="coin_balance"),
        CheckConstraint("ticket_balance BETWEEN 0 AND 99", name="ticket_balance"),
        Index(
            "ix_wallets_vip_until",
            "vip_until",
            postgresql_where=text("vip_until IS NOT NULL"),
        ),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    coin_balance: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    ticket_balance: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    vip_until: Mapped[datetime | None] = mapped_column(TS)
    vip_reminded_for: Mapped[datetime | None] = mapped_column(TS)
    equipped_frame_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("avatar_frames.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())


class WalletLedgerModel(Base):
    __tablename__ = "wallet_ledger"
    __table_args__ = (
        CheckConstraint("currency IN ('coin', 'ticket', 'vip_days')", name="currency"),
        CheckConstraint("amount <> 0", name="amount"),
        CheckConstraint(
            "reason IN ('season_reward', 'quest_bonus', 'streak_milestone', 'achievement', 'welcome',"
            " 'redemption', 'vip_unlock', 'admin_adjust')",
            name="reason",
        ),
        UniqueConstraint("user_id", "currency", "idempotency_key"),
        Index("ix_wallet_ledger_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    currency: Mapped[str] = mapped_column(String(8))
    amount: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int | None] = mapped_column(Integer)
    vip_until_after: Mapped[datetime | None] = mapped_column(TS)
    reason: Mapped[str] = mapped_column(String(20))
    idempotency_key: Mapped[str] = mapped_column(String(80))
    note: Mapped[str | None] = mapped_column(String(500))
    actor_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class VipUnlockModel(Base):
    __tablename__ = "vip_unlocks"
    __table_args__ = (
        CheckConstraint("source IN ('ticket', 'admin')", name="source"),
        Index("ix_vip_unlocks_series_id", "series_id"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    series_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("series.id", ondelete="CASCADE"), primary_key=True
    )
    source: Mapped[str] = mapped_column(String(8))
    unlocked_at: Mapped[datetime] = mapped_column(TS)


class UserFrameModel(Base):
    __tablename__ = "user_frames"
    __table_args__ = (
        CheckConstraint("source IN ('season', 'weekly_goal', 'redemption', 'admin')", name="source"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    frame_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("avatar_frames.id", ondelete="RESTRICT"), primary_key=True
    )
    source: Mapped[str] = mapped_column(String(12))
    acquired_at: Mapped[datetime] = mapped_column(TS)
    expires_at: Mapped[datetime | None] = mapped_column(TS)


class RewardItemModel(Base):
    __tablename__ = "reward_items"
    __table_args__ = (
        CheckConstraint("kind IN ('vip_days', 'vip_ticket', 'avatar_frame')", name="kind"),
        CheckConstraint("price_coins BETWEEN 1 AND 100000", name="price_coins"),
        CheckConstraint("vip_days BETWEEN 1 AND 365", name="vip_days"),
        CheckConstraint("ticket_count BETWEEN 1 AND 10", name="ticket_count"),
        CheckConstraint("per_user_limit >= 1", name="per_user_limit"),
        CheckConstraint(
            "(kind = 'vip_days') = (vip_days IS NOT NULL)"
            " AND (kind = 'vip_ticket') = (ticket_count IS NOT NULL)"
            " AND (kind = 'avatar_frame') = (frame_id IS NOT NULL)",
            name="kind_fields",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(12))
    price_coins: Mapped[int] = mapped_column(Integer)
    vip_days: Mapped[int | None] = mapped_column(SmallInteger)
    ticket_count: Mapped[int | None] = mapped_column(SmallInteger)
    frame_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("avatar_frames.id", ondelete="RESTRICT")
    )
    per_user_limit: Mapped[int | None] = mapped_column(SmallInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    sort_order: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())


class RewardRedemptionModel(Base):
    __tablename__ = "reward_redemptions"
    __table_args__ = (
        CheckConstraint("price_coins > 0", name="price_coins"),
        UniqueConstraint("user_id", "request_id"),
        Index("ix_reward_redemptions_user_id_item_id", "user_id", "item_id"),
        Index("ix_reward_redemptions_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("reward_items.id", ondelete="RESTRICT"))
    price_coins: Mapped[int] = mapped_column(Integer)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
