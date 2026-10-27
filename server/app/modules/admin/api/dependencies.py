"""Dependency cho router quản trị đặt trong module khác (`/admin/users/{user_id}/...`, F13.07)."""

from __future__ import annotations

from fastapi import Depends

from app.container import Container, get_container
from app.modules.admin.application.use_cases.ensure_target_user import EnsureTargetUserUseCase
from app.modules.admin.infrastructure.content_owner_notifier import NotificationsContentOwnerNotifier
from app.modules.admin.infrastructure.uow import SqlAdminUnitOfWork
from app.modules.auth.api.public import Identity, require_admin
from app.modules.notifications.application.public import SendNotificationUseCase
from app.modules.notifications.infrastructure.public import FileOutboxEmailSender, SqlNotificationsUnitOfWork


def build_ensure_target(container: Container) -> EnsureTargetUserUseCase:
    return EnsureTargetUserUseCase(lambda: SqlAdminUnitOfWork(container.session_factory))


def build_content_owner_notifier(container: Container) -> NotificationsContentOwnerNotifier:
    """Thông báo gỡ ảnh (F13.04) đi qua use case công khai của M14, không gửi email."""
    send = SendNotificationUseCase(
        lambda: SqlNotificationsUnitOfWork(container.session_factory),
        FileOutboxEmailSender(container.settings.storage_dir / "outbox"),
        container.clock,
    )
    return NotificationsContentOwnerNotifier(send)


async def get_target_user_id(
    user_id: int,
    admin: Identity = Depends(require_admin),
    container: Container = Depends(get_container),
) -> int:
    """Chỉ quản trị viên (403); người dùng đích phải tồn tại (404 `USER_NOT_FOUND`)."""
    await build_ensure_target(container).execute(admin, user_id)
    return user_id
