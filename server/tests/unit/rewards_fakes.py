"""Fake repository trong bộ nhớ cho test đơn vị của M17 (không cần CSDL)."""

from __future__ import annotations

import copy
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from app.modules.rewards.application.ports import Decoration, ExpiringVip
from app.modules.rewards.domain.entities import (
    AvatarFrame,
    Currency,
    FrameAcquireKind,
    ItemKind,
    LedgerEntry,
    NewLedgerEntry,
    NewRewardItem,
    Redemption,
    RewardItem,
    SeriesInfo,
    UserFrame,
    VipUnlock,
    Wallet,
)

NOW = datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc)

FRAMES = [
    AvatarFrame(1, "sakura_gold", "Hoa Anh Đào Vàng", None, "sakura_gold", FrameAcquireKind.SEASON),
    AvatarFrame(2, "spring_petal", "Cánh Hoa Mùa Xuân", None, "spring_petal", FrameAcquireKind.SEASON),
    AvatarFrame(3, "vip_sakura", "Khung VIP", None, "vip_sakura", FrameAcquireKind.VIP),
    AvatarFrame(4, "bamboo_leaf", "Lá Trúc Xanh", None, "bamboo_leaf", FrameAcquireKind.SHOP),
    AvatarFrame(5, "ink_cloud", "Mây Mực", None, "ink_cloud", FrameAcquireKind.SHOP),
]


def _item(i: int, code: str, kind: ItemKind, price: int, **extra: Any) -> RewardItem:
    return RewardItem(
        id=i,
        code=code,
        name=code,
        description=None,
        kind=kind,
        price_coins=price,
        vip_days=extra.get("vip_days"),
        ticket_count=extra.get("ticket_count"),
        frame_id=extra.get("frame_id"),
        per_user_limit=extra.get("per_user_limit"),
        is_active=True,
        sort_order=i,
        updated_by=None,
        created_at=NOW,
        updated_at=NOW,
    )


def default_items() -> list[RewardItem]:
    return [
        _item(1, "vip_1d", ItemKind.VIP_DAYS, 120, vip_days=1),
        _item(2, "vip_7d", ItemKind.VIP_DAYS, 700, vip_days=7),
        _item(3, "vip_ticket", ItemKind.VIP_TICKET, 300, ticket_count=1),
        _item(4, "frame_bamboo", ItemKind.AVATAR_FRAME, 800, frame_id=4),
        _item(5, "frame_ink", ItemKind.AVATAR_FRAME, 800, frame_id=5, per_user_limit=1),
    ]


class FakeWallets:
    def __init__(self) -> None:
        self.wallets: dict[int, Wallet] = {}
        self.ledger: list[LedgerEntry] = []
        self.user_frames: dict[tuple[int, int], UserFrame] = {}
        self.locks = 0

    async def lock_wallet(self, user_id: int, now: datetime) -> Wallet:
        self.locks += 1
        if user_id not in self.wallets:
            self.wallets[user_id] = Wallet(user_id, 0, 0, None, None, None, now, now)
        return replace(self.wallets[user_id])

    async def get_wallet(self, user_id: int) -> Wallet | None:
        found = self.wallets.get(user_id)
        return replace(found) if found else None

    async def save_wallet(self, wallet: Wallet, now: datetime) -> None:
        stored = self.wallets[wallet.user_id]
        self.wallets[wallet.user_id] = replace(
            wallet, vip_reminded_for=stored.vip_reminded_for, updated_at=now
        )

    async def has_ledger_key(self, user_id: int, currency: Currency, key: str) -> bool:
        return any(
            e.user_id == user_id and e.currency is currency and e.idempotency_key == key for e in self.ledger
        )

    async def add_ledger(self, entry: NewLedgerEntry) -> LedgerEntry:
        saved = LedgerEntry(
            id=len(self.ledger) + 1,
            user_id=entry.user_id,
            currency=entry.currency,
            amount=entry.amount,
            reason=entry.reason,
            idempotency_key=entry.idempotency_key,
            created_at=entry.created_at,
            balance_after=entry.balance_after,
            vip_until_after=entry.vip_until_after,
            note=entry.note,
            actor_id=entry.actor_id,
        )
        self.ledger.append(saved)
        return saved

    async def list_ledger(
        self, user_id: int, currency: Currency | None, offset: int, limit: int
    ) -> tuple[list[LedgerEntry], int]:
        rows = [e for e in reversed(self.ledger) if e.user_id == user_id and currency in (None, e.currency)]
        return rows[offset : offset + limit], len(rows)

    async def get_frame_by_code(self, code: str) -> AvatarFrame | None:
        return next((f for f in FRAMES if f.code == code), None)

    async def get_frame(self, frame_id: int) -> AvatarFrame | None:
        return next((f for f in FRAMES if f.id == frame_id), None)

    async def list_frames(self) -> list[AvatarFrame]:
        return list(FRAMES)

    async def get_user_frame(self, user_id: int, frame_id: int) -> UserFrame | None:
        return self.user_frames.get((user_id, frame_id))

    async def list_user_frames(self, user_id: int) -> list[UserFrame]:
        return [f for (uid, _), f in self.user_frames.items() if uid == user_id]

    async def save_user_frame(self, frame: UserFrame) -> None:
        self.user_frames[(frame.user_id, frame.frame_id)] = frame

    async def decorations(self, user_ids: Sequence[int], now: datetime) -> dict[int, Decoration]:
        result = {}
        for uid in user_ids:
            wallet = self.wallets.get(uid)
            if wallet is not None:
                result[uid] = Decoration(wallet.is_vip(now), None)
        return result

    async def list_expiring_vip(
        self, now: datetime, until: datetime, after_user_id: int, limit: int
    ) -> list[ExpiringVip]:
        rows = [
            ExpiringVip(w.user_id, w.vip_until)
            for w in sorted(self.wallets.values(), key=lambda w: w.user_id)
            if w.vip_until is not None
            and now < w.vip_until <= until
            and w.user_id > after_user_id
            and w.vip_reminded_for != w.vip_until
        ]
        return rows[:limit]

    async def mark_vip_reminded(self, user_id: int, vip_until: datetime) -> bool:
        wallet = self.wallets[user_id]
        if wallet.vip_until != vip_until:
            return False
        wallet.vip_reminded_for = vip_until
        return True


class FakeUnlocks:
    def __init__(self) -> None:
        self.items: dict[tuple[int, int], VipUnlock] = {}

    async def get(self, user_id: int, series_id: int) -> VipUnlock | None:
        return self.items.get((user_id, series_id))

    async def add(self, unlock: VipUnlock) -> None:
        self.items[(unlock.user_id, unlock.series_id)] = unlock

    async def list_for_user(self, user_id: int) -> list[VipUnlock]:
        return [u for (uid, _), u in self.items.items() if uid == user_id]


class FakeShop:
    def __init__(self) -> None:
        self.items = {i.id: i for i in default_items()}
        self.redemptions: list[Redemption] = []

    async def list_items(self, only_active: bool) -> list[RewardItem]:
        return sorted(
            (i for i in self.items.values() if i.is_active or not only_active),
            key=lambda i: (i.sort_order, i.id),
        )

    async def get_item(self, item_id: int) -> RewardItem | None:
        item = self.items.get(item_id)
        return replace(item) if item else None

    async def get_item_by_code(self, code: str) -> RewardItem | None:
        return next((replace(i) for i in self.items.values() if i.code == code), None)

    async def add_item(self, item: NewRewardItem) -> RewardItem:
        saved = RewardItem(
            id=max(self.items) + 1,
            code=item.code,
            name=item.name,
            description=item.description,
            kind=item.kind,
            price_coins=item.price_coins,
            vip_days=item.vip_days,
            ticket_count=item.ticket_count,
            frame_id=item.frame_id,
            per_user_limit=item.per_user_limit,
            is_active=item.is_active,
            sort_order=item.sort_order,
            updated_by=item.updated_by,
            created_at=item.created_at,
            updated_at=item.created_at,
        )
        self.items[saved.id] = saved
        return saved

    async def update_item(self, item: RewardItem, now: datetime) -> None:
        self.items[item.id] = replace(item, updated_at=now)

    async def count_redemptions_by_item(self, user_id: int) -> dict[int, int]:
        counts: dict[int, int] = {}
        for r in self.redemptions:
            if r.user_id == user_id:
                counts[r.item_id] = counts.get(r.item_id, 0) + 1
        return counts

    async def item_has_redemptions(self, item_id: int) -> bool:
        return any(r.item_id == item_id for r in self.redemptions)

    async def get_redemption(self, user_id: int, request_id: uuid.UUID) -> Redemption | None:
        return next(
            (r for r in self.redemptions if r.user_id == user_id and r.request_id == request_id), None
        )

    async def add_redemption(
        self, user_id: int, item_id: int, price_coins: int, request_id: uuid.UUID, now: datetime
    ) -> Redemption:
        saved = Redemption(len(self.redemptions) + 1, user_id, item_id, price_coins, request_id, now)
        self.redemptions.append(saved)
        return saved


class FakeSeries:
    def __init__(self) -> None:
        self.items: dict[int, SeriesInfo] = {}
        self.trial: set[int] = set()

    def add(
        self, series_id: int, *, public: bool = True, vip: bool = False, owner_id: int | None = None
    ) -> None:
        self.items[series_id] = SeriesInfo(series_id, f"Truyện {series_id}", public, owner_id, vip)

    async def get(self, series_id: int) -> SeriesInfo | None:
        return self.items.get(series_id)

    async def titles(self, series_ids: Sequence[int]) -> Mapping[int, str]:
        return {i: self.items[i].title for i in series_ids if i in self.items}

    async def set_vip(self, series_id: int, is_vip: bool) -> None:
        self.items[series_id] = replace(self.items[series_id], is_vip=is_vip)

    async def has_trial_chapter(self, series_id: int) -> bool:
        return series_id in self.trial


class FakeAudit:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str, str, int | None, dict[str, Any]]] = []

    async def add(
        self,
        admin_id: int,
        action: str,
        target_type: str,
        target_id: int | None,
        details: dict[str, Any],
        at: datetime,
    ) -> None:
        self.calls.append((admin_id, action, target_type, target_id, details))


class FakeRewardsUow:
    """Một "CSDL" dùng chung: mỗi lần mở giao dịch trả cùng đối tượng, `commit()` chỉ đếm số lần lưu."""

    def __init__(self) -> None:
        self.wallets = FakeWallets()
        self.unlocks = FakeUnlocks()
        self.shop = FakeShop()
        self.series = FakeSeries()
        self.audit = FakeAudit()
        self.commits = 0

    def _state(self) -> tuple[Any, ...]:
        return (
            self.wallets.wallets,
            self.wallets.ledger,
            self.wallets.user_frames,
            self.unlocks.items,
            self.shop.items,
            self.shop.redemptions,
            self.series.items,
            self.audit.calls,
        )

    async def __aenter__(self) -> FakeRewardsUow:
        self._snapshot = copy.deepcopy(self._state())
        return self

    async def __aexit__(self, exc_type: Any, *rest: Any) -> None:
        """Có lỗi thì khôi phục như rollback của giao dịch thật."""
        if exc_type is not None:
            (
                self.wallets.wallets,
                self.wallets.ledger,
                self.wallets.user_frames,
                self.unlocks.items,
                self.shop.items,
                self.shop.redemptions,
                self.series.items,
                self.audit.calls,
            ) = self._snapshot

    async def commit(self) -> None:
        self.commits += 1


class FakeNotifier:
    def __init__(self, fail: bool = False) -> None:
        self.events: list[tuple[str, int]] = []
        self.fail = fail

    async def vip_granted(self, user_id: int, days: int, vip_until: datetime, reason: str | None) -> None:
        self.events.append(("vip_granted", user_id))

    async def vip_revoked(self, user_id: int, reason: str | None) -> None:
        self.events.append(("vip_revoked", user_id))

    async def wallet_adjusted(self, user_id: int, currency: Currency, amount: int, reason: str) -> None:
        self.events.append(("wallet_adjusted", user_id))

    async def vip_expiring(self, user_id: int, vip_until: datetime) -> None:
        if self.fail:
            raise RuntimeError("gửi lỗi")
        self.events.append(("vip_expiring", user_id))
