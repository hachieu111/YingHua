"""Giao diện (port) mà tầng hạ tầng của M17 phải hiện thực."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.modules.admin.application.public import AuditLogRepository
from app.modules.rewards.domain.entities import (
    AvatarFrame,
    Currency,
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


@dataclass(frozen=True, slots=True)
class ExpiringVip:
    """Người có hạn VIP sắp hết, kèm trạng thái đã được nhắc cho hạn đó chưa."""

    user_id: int
    vip_until: datetime


@dataclass(frozen=True, slots=True)
class Decoration:
    """Khung và dấu VIP đang hiệu lực của một người (F17.08)."""

    is_vip: bool
    frame: AvatarFrame | None


class WalletRepository(Protocol):
    async def lock_wallet(self, user_id: int, now: datetime) -> Wallet:
        """Tạo ví nếu chưa có rồi khóa dòng (`SELECT ... FOR UPDATE`) cho tới hết giao dịch."""
        ...

    async def get_wallet(self, user_id: int) -> Wallet | None: ...

    async def save_wallet(self, wallet: Wallet, now: datetime) -> None: ...

    async def has_ledger_key(self, user_id: int, currency: Currency, key: str) -> bool: ...

    async def add_ledger(self, entry: NewLedgerEntry) -> LedgerEntry: ...

    async def list_ledger(
        self, user_id: int, currency: Currency | None, offset: int, limit: int
    ) -> tuple[list[LedgerEntry], int]:
        """Mới nhất trước."""
        ...

    async def get_frame_by_code(self, code: str) -> AvatarFrame | None: ...

    async def get_frame(self, frame_id: int) -> AvatarFrame | None: ...

    async def list_frames(self) -> list[AvatarFrame]:
        """Mọi khung đang dùng."""
        ...

    async def get_user_frame(self, user_id: int, frame_id: int) -> UserFrame | None: ...

    async def list_user_frames(self, user_id: int) -> list[UserFrame]: ...

    async def save_user_frame(self, frame: UserFrame) -> None:
        """Thêm hoặc ghi đè (khóa chính `(user_id, frame_id)`)."""
        ...

    async def decorations(self, user_ids: Sequence[int], now: datetime) -> dict[int, Decoration]:
        """Khung đang hiệu lực và dấu VIP của nhiều người bằng một truy vấn (không N+1)."""
        ...

    async def list_expiring_vip(
        self, now: datetime, until: datetime, after_user_id: int, limit: int
    ) -> list[ExpiringVip]:
        """Tài khoản đang hoạt động có `now < vip_until <= until` mà chưa được nhắc cho đúng hạn đó."""
        ...

    async def mark_vip_reminded(self, user_id: int, vip_until: datetime) -> bool:
        """Ghi `vip_reminded_for = vip_until` nếu hạn VIP vẫn như cũ. True nếu đã ghi."""
        ...


class UnlockRepository(Protocol):
    async def get(self, user_id: int, series_id: int) -> VipUnlock | None: ...

    async def add(self, unlock: VipUnlock) -> None: ...

    async def list_for_user(self, user_id: int) -> list[VipUnlock]: ...


class ShopRepository(Protocol):
    async def list_items(self, only_active: bool) -> list[RewardItem]:
        """Theo `sort_order` rồi `id`."""
        ...

    async def get_item(self, item_id: int) -> RewardItem | None: ...

    async def get_item_by_code(self, code: str) -> RewardItem | None: ...

    async def add_item(self, item: NewRewardItem) -> RewardItem: ...

    async def update_item(self, item: RewardItem, now: datetime) -> None: ...

    async def count_redemptions_by_item(self, user_id: int) -> dict[int, int]:
        """Số lượt đổi của người này theo từng món."""
        ...

    async def item_has_redemptions(self, item_id: int) -> bool: ...

    async def get_redemption(self, user_id: int, request_id: uuid.UUID) -> Redemption | None: ...

    async def add_redemption(
        self, user_id: int, item_id: int, price_coins: int, request_id: uuid.UUID, now: datetime
    ) -> Redemption: ...


class SeriesCatalog(Protocol):
    """Đọc và đặt cờ VIP của bảng `series` (thuộc M03); M17 không biết gì thêm về truyện."""

    async def get(self, series_id: int) -> SeriesInfo | None: ...

    async def titles(self, series_ids: Sequence[int]) -> Mapping[int, str]: ...

    async def set_vip(self, series_id: int, is_vip: bool) -> None: ...

    async def has_trial_chapter(self, series_id: int) -> bool: ...


class RewardsUnitOfWork(Protocol):
    """Một giao dịch. Không gọi commit() thì mọi thay đổi bị hủy khi thoát khối `async with`."""

    @property
    def wallets(self) -> WalletRepository: ...

    @property
    def unlocks(self) -> UnlockRepository: ...

    @property
    def shop(self) -> ShopRepository: ...

    @property
    def series(self) -> SeriesCatalog: ...

    @property
    def audit(self) -> AuditLogRepository: ...

    async def __aenter__(self) -> RewardsUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...

    async def commit(self) -> None: ...


class RewardNotifier(Protocol):
    """Gửi thông báo trong ứng dụng (M14, F14.05). Hiện thực tự bắt lỗi gửi, không làm hỏng thao tác."""

    async def vip_granted(self, user_id: int, days: int, vip_until: datetime, reason: str | None) -> None: ...

    async def vip_revoked(self, user_id: int, reason: str | None) -> None: ...

    async def wallet_adjusted(self, user_id: int, currency: Currency, amount: int, reason: str) -> None: ...

    async def vip_expiring(self, user_id: int, vip_until: datetime) -> None:
        """Có thể raise nếu gửi lỗi để tác vụ nền không ghi "đã nhắc" (F17.03)."""
        ...
