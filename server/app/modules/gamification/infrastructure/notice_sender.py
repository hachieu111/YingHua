"""Cầu nối M16 -> M14: gửi thông báo trong ứng dụng sau khi giao dịch thưởng đã lưu (F14.05)."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import Clock
from app.modules.gamification.application.dto import Notice
from app.modules.notifications.application.public import (
    NotificationKind,
    NotificationRequest,
    SendNotificationUseCase,
)
from app.modules.notifications.infrastructure.public import SqlNotificationsUnitOfWork

logger = logging.getLogger(__name__)


class _NoEmail:
    """Thông báo của M16 chỉ ở trong ứng dụng (không có `email_to`), nên không bao giờ được gọi gửi email."""

    async def send(self, to_email: str, subject: str, body: str) -> None:
        raise RuntimeError("Thông báo của M16 không gửi email")


class _FixedClock:
    def __init__(self, at: datetime) -> None:
        self._at = at

    def now(self) -> datetime:
        return self._at


class NotificationsNoticeSender:
    """Gọi use case công khai F14.05 của M14 trong giao dịch riêng. Lỗi gửi chỉ ghi log, thưởng vẫn giữ."""

    def __init__(self, send: SendNotificationUseCase) -> None:
        self._send = send

    async def send(self, notice: Notice) -> None:
        try:
            await self._send.execute(
                NotificationRequest(
                    user_id=notice.user_id,
                    kind=NotificationKind(notice.kind),
                    title=notice.title,
                    body=notice.body,
                    data=dict(notice.data),
                )
            )
        except Exception:
            logger.warning(
                "Không gửi được thông báo %s cho user_id=%s", notice.kind, notice.user_id, exc_info=True
            )


def build_notice_sender(
    session_factory: async_sessionmaker[AsyncSession], clock: Clock
) -> NotificationsNoticeSender:
    send = SendNotificationUseCase(lambda: SqlNotificationsUnitOfWork(session_factory), _NoEmail(), clock)
    return NotificationsNoticeSender(send)


def build_notice_sender_for_session(session: AsyncSession, at: datetime) -> NotificationsNoticeSender:
    """Gửi thông báo bằng cùng engine với phiên của module nguồn (chỉ có phiên, không có factory)."""
    assert session.bind is not None
    factory = async_sessionmaker(session.bind, expire_on_commit=False)
    return build_notice_sender(factory, _FixedClock(at))
