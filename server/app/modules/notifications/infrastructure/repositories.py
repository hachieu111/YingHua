from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import case, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.domain.entities import (
    Channel,
    DeliveryStatus,
    ErrorReport,
    NewErrorReport,
    NewNotification,
    Notification,
    NotificationKind,
    ReportStatus,
    ReportType,
)
from app.modules.notifications.domain.errors import DuplicateReportError
from app.modules.notifications.infrastructure.orm_models import (
    ErrorReportModel,
    NotificationModel,
    ReminderLogModel,
)


def _report(m: ErrorReportModel) -> ErrorReport:
    return ErrorReport(
        id=m.id,
        reporter_id=m.reporter_id,
        page_id=m.page_id,
        bubble_id=m.bubble_id,
        report_type=ReportType(m.report_type),
        description=m.description,
        status=ReportStatus(m.status),
        created_at=m.created_at,
        resolution_note=m.resolution_note,
        handled_by=m.handled_by,
        handled_at=m.handled_at,
    )


def _notification(m: NotificationModel) -> Notification:
    return Notification(
        id=m.id,
        user_id=m.user_id,
        kind=NotificationKind(m.kind),
        title=m.title,
        body=m.body,
        channel=Channel(m.channel),
        status=DeliveryStatus(m.status),
        created_at=m.created_at,
        data=dict(m.data or {}),
        read_at=m.read_at,
        sent_at=m.sent_at,
    )


class SqlErrorReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, new_report: NewErrorReport) -> ErrorReport:
        model = ErrorReportModel(
            reporter_id=new_report.reporter_id,
            page_id=new_report.page_id,
            bubble_id=new_report.bubble_id,
            report_type=new_report.report_type.value,
            description=new_report.description,
            status=ReportStatus.NEW.value,
            created_at=new_report.created_at,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(model)
                await self._session.flush()
        except IntegrityError as exc:  # hai yêu cầu đồng thời cùng báo một lỗi: chỉ mục duy nhất từng phần
            existing = await self.find_open(
                new_report.reporter_id, new_report.page_id, new_report.bubble_id, new_report.report_type
            )
            raise DuplicateReportError(details={"report_id": existing.id if existing else None}) from exc
        return _report(model)

    async def find_open(
        self, reporter_id: int, page_id: int | None, bubble_id: int | None, report_type: ReportType
    ) -> ErrorReport | None:
        stmt = select(ErrorReportModel).where(
            ErrorReportModel.reporter_id == reporter_id,
            ErrorReportModel.report_type == report_type.value,
            ErrorReportModel.status == ReportStatus.NEW.value,
            ErrorReportModel.page_id.is_(None) if page_id is None else ErrorReportModel.page_id == page_id,
            ErrorReportModel.bubble_id.is_(None)
            if bubble_id is None
            else ErrorReportModel.bubble_id == bubble_id,
        )
        model = (await self._session.execute(stmt)).scalars().first()
        return _report(model) if model else None

    async def get_for_update(self, report_id: int) -> ErrorReport | None:
        model = await self._session.get(ErrorReportModel, report_id, with_for_update=True)
        return _report(model) if model else None

    async def save(self, report: ErrorReport) -> None:
        model = await self._session.get(ErrorReportModel, report.id)
        if model is None:
            return
        model.status = report.status.value
        model.resolution_note = report.resolution_note
        model.handled_by = report.handled_by
        model.handled_at = report.handled_at
        await self._session.flush()

    async def list_for_reporter(
        self, reporter_id: int, offset: int, limit: int
    ) -> tuple[list[ErrorReport], int]:
        where = ErrorReportModel.reporter_id == reporter_id
        total = (
            await self._session.execute(select(func.count(ErrorReportModel.id)).where(where))
        ).scalar_one()
        rows = await self._session.scalars(
            select(ErrorReportModel)
            .where(where)
            .order_by(ErrorReportModel.created_at.desc(), ErrorReportModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_report(m) for m in rows], int(total)

    async def search(
        self, status: ReportStatus | None, reporter_id: int | None, offset: int, limit: int
    ) -> tuple[list[ErrorReport], int]:
        conditions = []
        if status is not None:
            conditions.append(ErrorReportModel.status == status.value)
        if reporter_id is not None:
            conditions.append(ErrorReportModel.reporter_id == reporter_id)
        total = (
            await self._session.execute(select(func.count(ErrorReportModel.id)).where(*conditions))
        ).scalar_one()
        is_new_first = case((ErrorReportModel.status == ReportStatus.NEW.value, 0), else_=1)
        rows = await self._session.scalars(
            select(ErrorReportModel)
            .where(*conditions)
            .order_by(is_new_first, ErrorReportModel.created_at.desc(), ErrorReportModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_report(m) for m in rows], int(total)


class SqlNotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, new_notification: NewNotification) -> Notification:
        model = NotificationModel(
            user_id=new_notification.user_id,
            kind=new_notification.kind.value,
            title=new_notification.title,
            body=new_notification.body,
            channel=new_notification.channel.value,
            status=new_notification.status.value,
            data=new_notification.data,
            created_at=new_notification.created_at,
            sent_at=new_notification.sent_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _notification(model)

    async def set_delivery(self, notification_id: int, status: str, sent_at: datetime | None) -> None:
        await self._session.execute(
            update(NotificationModel)
            .where(NotificationModel.id == notification_id)
            .values(status=status, sent_at=sent_at)
        )

    async def list_in_app(
        self, user_id: int, unread_only: bool, offset: int, limit: int
    ) -> tuple[list[Notification], int]:
        conditions = [NotificationModel.user_id == user_id, NotificationModel.channel == Channel.IN_APP.value]
        if unread_only:
            conditions.append(NotificationModel.read_at.is_(None))
        total = (
            await self._session.execute(select(func.count(NotificationModel.id)).where(*conditions))
        ).scalar_one()
        rows = await self._session.scalars(
            select(NotificationModel)
            .where(*conditions)
            .order_by(NotificationModel.created_at.desc(), NotificationModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_notification(m) for m in rows], int(total)

    async def count_unread(self, user_id: int) -> int:
        stmt = select(func.count(NotificationModel.id)).where(
            NotificationModel.user_id == user_id,
            NotificationModel.channel == Channel.IN_APP.value,
            NotificationModel.read_at.is_(None),
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def mark_read(self, user_id: int, notification_id: int, now: datetime) -> bool:
        owned = await self._session.execute(
            select(NotificationModel.id).where(
                NotificationModel.id == notification_id,
                NotificationModel.user_id == user_id,
                NotificationModel.channel == Channel.IN_APP.value,
            )
        )
        if owned.first() is None:
            return False
        await self._session.execute(
            update(NotificationModel)
            .where(NotificationModel.id == notification_id, NotificationModel.read_at.is_(None))
            .values(read_at=now)
        )
        return True

    async def mark_all_read(self, user_id: int, now: datetime) -> int:
        result = await self._session.execute(
            update(NotificationModel)
            .where(
                NotificationModel.user_id == user_id,
                NotificationModel.channel == Channel.IN_APP.value,
                NotificationModel.read_at.is_(None),
            )
            .values(read_at=now)
        )
        return int(getattr(result, "rowcount", 0) or 0)


class SqlReminderLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim(self, user_id: int, day: date, now: datetime) -> bool:
        stmt = (
            insert(ReminderLogModel)
            .values(user_id=user_id, reminder_date=day, sent_at=now)
            .on_conflict_do_nothing(index_elements=["user_id", "reminder_date"])
            .returning(ReminderLogModel.user_id)
        )
        return (await self._session.execute(stmt)).first() is not None
