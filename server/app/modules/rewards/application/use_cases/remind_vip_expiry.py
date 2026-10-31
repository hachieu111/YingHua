from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from app.modules.rewards.application.dto import VipReminderReport
from app.modules.rewards.application.ports import RewardNotifier, RewardsUnitOfWork
from app.modules.rewards.domain.rules import VIP_REMINDER_WINDOW

logger = logging.getLogger(__name__)

BATCH_SIZE = 200


class RemindVipExpiryUseCase:
    """F17.03, US-HG-06 - Tác vụ nền `remind_vip_expiry`: nhắc người có hạn VIP trong vòng 24 giờ tới.

    Mỗi hạn VIP chỉ nhắc một lần (`wallets.vip_reminded_for`); được cộng thêm ngày thì hạn đổi nên được
    nhắc lại cho hạn mới. Tài khoản bị khóa không được nhắc. Gửi lỗi: ghi log, KHÔNG ghi "đã nhắc",
    lần chạy sau thử lại.
    """

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork], notifier: RewardNotifier) -> None:
        self._uow_factory = uow_factory
        self._notifier = notifier

    async def execute(self, now: datetime) -> VipReminderReport:
        report = VipReminderReport()
        until, after = now + VIP_REMINDER_WINDOW, 0
        while True:
            async with self._uow_factory() as uow:
                batch = await uow.wallets.list_expiring_vip(now, until, after, BATCH_SIZE)
            for item in batch:
                report = replace(report, scanned=report.scanned + 1)
                try:
                    await self._notifier.vip_expiring(item.user_id, item.vip_until)
                except Exception:
                    logger.exception("Gửi nhắc VIP sắp hết hạn lỗi, user_id=%s", item.user_id)
                    report = replace(report, failed=report.failed + 1)
                    continue
                async with self._uow_factory() as uow:
                    marked = await uow.wallets.mark_vip_reminded(item.user_id, item.vip_until)
                    await uow.commit()
                report = replace(report, reminded=report.reminded + (1 if marked else 0))
            if len(batch) < BATCH_SIZE:
                return report
            after = batch[-1].user_id
