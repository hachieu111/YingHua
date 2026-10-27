from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends

from app.container import Container, get_container
from app.modules.library.application.public import LibraryPageAccess
from app.modules.library.infrastructure.public import SqlLibraryUnitOfWork
from app.modules.notifications.application.ports import NotificationsUnitOfWork
from app.modules.notifications.application.use_cases.count_unread_notifications import (
    CountUnreadNotificationsUseCase,
)
from app.modules.notifications.application.use_cases.create_error_report import CreateErrorReportUseCase
from app.modules.notifications.application.use_cases.list_error_reports import ListErrorReportsUseCase
from app.modules.notifications.application.use_cases.list_my_reports import ListMyReportsUseCase
from app.modules.notifications.application.use_cases.list_notifications import ListNotificationsUseCase
from app.modules.notifications.application.use_cases.mark_all_notifications_read import (
    MarkAllNotificationsReadUseCase,
)
from app.modules.notifications.application.use_cases.mark_notification_read import MarkNotificationReadUseCase
from app.modules.notifications.application.use_cases.resolve_error_report import ResolveErrorReportUseCase
from app.modules.notifications.infrastructure.public import FileOutboxEmailSender, SqlNotificationsUnitOfWork


@dataclass(slots=True)
class NotificationServices:
    create_report: CreateErrorReportUseCase
    my_reports: ListMyReportsUseCase
    list_reports: ListErrorReportsUseCase
    resolve_report: ResolveErrorReportUseCase
    list_notifications: ListNotificationsUseCase
    count_unread: CountUnreadNotificationsUseCase
    mark_read: MarkNotificationReadUseCase
    mark_all_read: MarkAllNotificationsReadUseCase


def build_notification_services(container: Container) -> NotificationServices:
    factory = container.session_factory
    clock = container.clock

    def uow_factory() -> NotificationsUnitOfWork:
        return SqlNotificationsUnitOfWork(factory)

    pages = LibraryPageAccess(lambda: SqlLibraryUnitOfWork(factory), clock)
    email = FileOutboxEmailSender(container.settings.storage_dir / "outbox")
    return NotificationServices(
        create_report=CreateErrorReportUseCase(uow_factory, pages, clock),
        my_reports=ListMyReportsUseCase(uow_factory, pages),
        list_reports=ListErrorReportsUseCase(uow_factory, pages),
        resolve_report=ResolveErrorReportUseCase(uow_factory, pages, email, clock),
        list_notifications=ListNotificationsUseCase(uow_factory),
        count_unread=CountUnreadNotificationsUseCase(uow_factory),
        mark_read=MarkNotificationReadUseCase(uow_factory, clock),
        mark_all_read=MarkAllNotificationsReadUseCase(uow_factory, clock),
    )


def get_notification_services(container: Container = Depends(get_container)) -> NotificationServices:
    return build_notification_services(container)
