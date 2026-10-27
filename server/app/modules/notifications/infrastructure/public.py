"""Hiện thực M14 mà tầng lắp ghép (API, worker) được dùng."""

from __future__ import annotations

from app.modules.notifications.infrastructure.email_outbox import FileOutboxEmailSender
from app.modules.notifications.infrastructure.uow import SqlNotificationsUnitOfWork

__all__ = ["FileOutboxEmailSender", "SqlNotificationsUnitOfWork"]
