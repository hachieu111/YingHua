from __future__ import annotations

from app.core.db import SqlAlchemyUnitOfWork
from app.modules.admin.infrastructure.public import SqlAuditLogRepository
from app.modules.auth.infrastructure.public import SqlUserRepository
from app.modules.imaging.infrastructure.public import SqlBubbleRepository
from app.modules.notifications.infrastructure.repositories import (
    SqlErrorReportRepository,
    SqlNotificationRepository,
    SqlReminderLogRepository,
)
from app.modules.settings.infrastructure.public import SqlReminderSettingsSource


class SqlNotificationsUnitOfWork(SqlAlchemyUnitOfWork):
    reports: SqlErrorReportRepository
    notifications: SqlNotificationRepository
    reminders: SqlReminderLogRepository
    reminder_settings: SqlReminderSettingsSource
    bubbles: SqlBubbleRepository
    users: SqlUserRepository
    audit: SqlAuditLogRepository

    def _init_repositories(self) -> None:
        self.reports = SqlErrorReportRepository(self.session)
        self.notifications = SqlNotificationRepository(self.session)
        self.reminders = SqlReminderLogRepository(self.session)
        self.reminder_settings = SqlReminderSettingsSource(self.session)
        self.bubbles = SqlBubbleRepository(self.session)
        self.users = SqlUserRepository(self.session)
        self.audit = SqlAuditLogRepository(self.session)
