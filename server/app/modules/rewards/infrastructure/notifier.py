"""Cầu nối M17 -> M14: thông báo trong ứng dụng cho VIP và ví (F14.05)."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import Clock
from app.modules.notifications.application.public import (
    NotificationKind,
    NotificationRequest,
    SendNotificationUseCase,
)
from app.modules.notifications.infrastructure.public import FileOutboxEmailSender, SqlNotificationsUnitOfWork
from app.modules.rewards.domain.entities import Currency
from app.modules.rewards.domain.rules import format_vietnam_time

logger = logging.getLogger(__name__)

_CURRENCY_LABELS = {Currency.COIN: "xu Sakura", Currency.TICKET: "vé đọc truyện VIP"}


def build_reward_notifier(
    session_factory: async_sessionmaker[AsyncSession], outbox_dir: Path, clock: Clock
) -> NotificationsRewardNotifier:
    """Lắp thông báo của M17 vào use case công khai F14.05 của M14 (chỉ thông báo trong ứng dụng)."""
    send = SendNotificationUseCase(
        lambda: SqlNotificationsUnitOfWork(session_factory), FileOutboxEmailSender(outbox_dir), clock
    )
    return NotificationsRewardNotifier(send)


class NotificationsRewardNotifier:
    """Gọi use case công khai F14.05 của M14. Thông báo gửi sau khi giao dịch thưởng đã lưu: lỗi gửi chỉ ghi
    log (phần thưởng vẫn giữ), riêng `vip_expiring` raise để tác vụ nền không ghi "đã nhắc" (F17.03)."""

    def __init__(self, send: SendNotificationUseCase) -> None:
        self._send = send

    async def vip_granted(self, user_id: int, days: int, vip_until: datetime, reason: str | None) -> None:
        body = f"Hạn VIP mới: {format_vietnam_time(vip_until)}."
        if reason:
            body += f" Lý do: {reason}"
        await self._safe(
            user_id,
            NotificationKind.VIP_GRANTED,
            f"Bạn được tặng {days} ngày VIP",
            body,
            {"days": days, "vip_until": vip_until.isoformat()},
        )

    async def vip_revoked(self, user_id: int, reason: str | None) -> None:
        body = f"Lý do: {reason}" if reason else None
        await self._safe(
            user_id,
            NotificationKind.WALLET_ADJUSTED,
            "VIP của bạn đã bị thu hồi",
            body,
            {"currency": "vip_days"},
        )

    async def wallet_adjusted(self, user_id: int, currency: Currency, amount: int, reason: str) -> None:
        label = _CURRENCY_LABELS.get(currency, currency.value)
        sign = "+" if amount > 0 else ""
        await self._safe(
            user_id,
            NotificationKind.WALLET_ADJUSTED,
            f"Ví của bạn được điều chỉnh: {sign}{amount} {label}",
            f"Lý do: {reason}",
            {"currency": currency.value, "amount": amount},
        )

    async def vip_expiring(self, user_id: int, vip_until: datetime) -> None:
        await self._send.execute(
            NotificationRequest(
                user_id=user_id,
                kind=NotificationKind.VIP_EXPIRING,
                title="VIP của bạn sắp hết hạn",
                body=f"VIP sẽ hết hạn lúc {format_vietnam_time(vip_until)}. "
                "Dùng quyền lợi VIP hoặc đổi thêm ngày VIP ở cửa hàng.",
                data={"vip_until": vip_until.isoformat()},
            )
        )

    async def _safe(
        self, user_id: int, kind: NotificationKind, title: str, body: str | None, data: dict[str, Any]
    ) -> None:
        try:
            await self._send.execute(
                NotificationRequest(user_id=user_id, kind=kind, title=title, body=body, data=data)
            )
        except Exception:
            logger.warning("Không gửi được thông báo %s cho user_id=%s", kind.value, user_id, exc_info=True)
