from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta

from app.modules.notifications.application.delivery import deliver_notification
from app.modules.notifications.application.dto import NotificationRequest, ReminderConfig, ReminderReport
from app.modules.notifications.application.ports import DueCardCounter, EmailSender, NotificationsUnitOfWork
from app.modules.notifications.domain.entities import NotificationKind
from app.modules.notifications.domain.rules import reminder_day_if_due, reminder_message

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


class SendDueRemindersUseCase:
    """F14.04 — Quét người học đã bật nhắc, tới giờ thì gửi đúng MỘT lời nhắc mỗi ngày (US-HG-04, US-NH-59).

    Điều kiện gửi: đã bật nhắc, giờ địa phương (theo múi giờ của họ) nằm trong [giờ nhắc, giờ nhắc + khung
    chờ] của hôm nay, tài khoản không bị khóa, còn thẻ đến hạn (F08.01; đã ôn xong thì không còn thẻ đến hạn).
    Nhật ký nhắc của ngày được ghi trước khi gửi, nên gửi lỗi (email) cũng không bị gửi lặp trong ngày.
    Lời nhắc gồm thông báo trong ứng dụng và email (F14.05); email lỗi không làm mất thông báo trong ứng dụng.
    """

    def __init__(
        self,
        uow_factory: Callable[[], NotificationsUnitOfWork],
        due_cards: DueCardCounter,
        email: EmailSender,
        config: ReminderConfig,
    ) -> None:
        self._uow_factory = uow_factory
        self._due_cards = due_cards
        self._email = email
        self._grace = timedelta(hours=config.grace_hours)

    async def execute(self, now: datetime) -> ReminderReport:
        report = ReminderReport()
        after = 0
        while True:
            async with self._uow_factory() as uow:
                batch = await uow.reminder_settings.list_enabled(after, BATCH_SIZE)
                users = await uow.users.get_many([c.user_id for c in batch])
            if not batch:
                return report
            for setting in batch:
                report = replace(report, scanned=report.scanned + 1)
                day = reminder_day_if_due(now, setting.timezone, setting.reminder_time, self._grace)
                if day is None:
                    report = replace(report, skipped_not_due_time=report.skipped_not_due_time + 1)
                    continue
                user = users.get(setting.user_id)
                if user is None or user.is_locked:
                    report = replace(report, skipped_locked=report.skipped_locked + 1)
                    continue
                due = await self._due_cards.count_due(user.id, now)
                if due <= 0:
                    report = replace(report, skipped_no_cards=report.skipped_no_cards + 1)
                    continue
                async with self._uow_factory() as uow:
                    if not await uow.reminders.claim(user.id, day, now):
                        report = replace(report, skipped_already=report.skipped_already + 1)
                        continue
                    title, body = reminder_message(due)
                    outcome = await deliver_notification(
                        uow,
                        self._email,
                        NotificationRequest(
                            user_id=user.id,
                            kind=NotificationKind.REMINDER,
                            title=title,
                            body=body,
                            data={"due_cards": due},
                            email_to=user.email,
                        ),
                        now,
                    )
                    await uow.commit()
                report = replace(
                    report,
                    sent=report.sent + 1,
                    email_failed=report.email_failed + (1 if outcome.email_failed else 0),
                )
            after = batch[-1].user_id
            if len(batch) < BATCH_SIZE:
                return report
