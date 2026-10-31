"""Thực thể của M17 VIP & Phần thưởng - thuần Python, không phụ thuộc framework."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Currency(str, Enum):
    COIN = "coin"  # xu Sakura
    TICKET = "ticket"  # vé đọc truyện VIP
    VIP_DAYS = "vip_days"  # ngày VIP


class LedgerReason(str, Enum):
    """Danh sách lý do cố định của sổ phần thưởng (F17.01)."""

    SEASON_REWARD = "season_reward"
    QUEST_BONUS = "quest_bonus"
    STREAK_MILESTONE = "streak_milestone"
    ACHIEVEMENT = "achievement"
    WELCOME = "welcome"
    REDEMPTION = "redemption"
    VIP_UNLOCK = "vip_unlock"
    ADMIN_ADJUST = "admin_adjust"


class FrameAcquireKind(str, Enum):
    SEASON = "season"  # thưởng mùa / mục tiêu tuần: không bán
    SHOP = "shop"  # đổi ở cửa hàng
    VIP = "vip"  # dùng được khi đang VIP, không cần sở hữu


class FrameSource(str, Enum):
    SEASON = "season"
    WEEKLY_GOAL = "weekly_goal"
    REDEMPTION = "redemption"
    ADMIN = "admin"


class ItemKind(str, Enum):
    VIP_DAYS = "vip_days"
    VIP_TICKET = "vip_ticket"
    AVATAR_FRAME = "avatar_frame"


class UnlockSource(str, Enum):
    TICKET = "ticket"
    ADMIN = "admin"


@dataclass(slots=True)
class Wallet:
    """Ví 1-1 với người dùng (F17.01). `vip_until` chỉ là hạn; có đang VIP hay không tính theo `now`."""

    user_id: int
    coin_balance: int
    ticket_balance: int
    vip_until: datetime | None
    vip_reminded_for: datetime | None
    equipped_frame_id: int | None
    created_at: datetime
    updated_at: datetime

    def is_vip(self, now: datetime) -> bool:
        return self.vip_until is not None and self.vip_until > now


@dataclass(frozen=True, slots=True)
class NewLedgerEntry:
    user_id: int
    currency: Currency
    amount: int  # dương là nhận, âm là tiêu/thu
    reason: LedgerReason
    idempotency_key: str
    created_at: datetime
    balance_after: int | None = None  # xu, vé
    vip_until_after: datetime | None = None  # chỉ ngày VIP
    note: str | None = None
    actor_id: int | None = None


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    id: int
    user_id: int
    currency: Currency
    amount: int
    reason: LedgerReason
    idempotency_key: str
    created_at: datetime
    balance_after: int | None = None
    vip_until_after: datetime | None = None
    note: str | None = None
    actor_id: int | None = None


@dataclass(frozen=True, slots=True)
class AvatarFrame:
    id: int
    code: str
    name: str
    description: str | None
    style_key: str
    acquire_kind: FrameAcquireKind
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class UserFrame:
    """Khung người dùng sở hữu; `expires_at` None là vĩnh viễn."""

    user_id: int
    frame_id: int
    source: FrameSource
    acquired_at: datetime
    expires_at: datetime | None = None

    def is_valid(self, now: datetime) -> bool:
        return self.expires_at is None or self.expires_at > now

    @property
    def is_permanent(self) -> bool:
        return self.expires_at is None


@dataclass(frozen=True, slots=True)
class VipUnlock:
    user_id: int
    series_id: int
    source: UnlockSource
    unlocked_at: datetime


@dataclass(slots=True)
class RewardItem:
    id: int
    code: str
    name: str
    description: str | None
    kind: ItemKind
    price_coins: int
    vip_days: int | None
    ticket_count: int | None
    frame_id: int | None
    per_user_limit: int | None
    is_active: bool
    sort_order: int
    updated_by: int | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class NewRewardItem:
    code: str
    name: str
    description: str | None
    kind: ItemKind
    price_coins: int
    vip_days: int | None
    ticket_count: int | None
    frame_id: int | None
    per_user_limit: int | None
    is_active: bool
    sort_order: int
    updated_by: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Redemption:
    id: int
    user_id: int
    item_id: int
    price_coins: int
    request_id: uuid.UUID
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SeriesInfo:
    """Phần của truyện (M03) mà M17 cần: quyền xem và cờ VIP."""

    id: int
    title: str
    is_public: bool
    owner_id: int | None
    is_vip: bool


@dataclass(frozen=True, slots=True)
class FrameGrant:
    """Khung được trao: `days` None là vĩnh viễn, có số ngày thì hết hạn sau ngần ấy ngày kể từ lúc trao."""

    code: str
    source: FrameSource
    days: int | None = None


@dataclass(frozen=True, slots=True)
class RewardBundle:
    """Gói thưởng hoặc khoản trừ (số âm = trừ) của F17.01."""

    coins: int = 0
    tickets: int = 0
    vip_days: int = 0
    frame: FrameGrant | None = None

    @property
    def has_currency(self) -> bool:
        return bool(self.coins or self.tickets or self.vip_days)
