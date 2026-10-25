"""Quyền truy cập dữ liệu của người khác dành cho quản trị viên (F13.07, security.md)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.errors import PermissionDeniedError
from app.modules.admin.application.ports import AuditLogRepository
from app.modules.auth.application.public import Identity


def resolve_owner(actor: Identity, target_user_id: int | None) -> int:
    """Mã người sở hữu dữ liệu mà use case sẽ thao tác.

    Không chỉ định người đích (hoặc đích là chính mình) thì là chủ sở hữu; người khác thì chỉ quản trị viên
    được phép. Người dùng thường không có đường nào tới dữ liệu của người khác nên API thường không đổi.
    """
    if target_user_id is None or target_user_id == actor.user_id:
        return actor.user_id
    if not actor.is_admin:
        raise PermissionDeniedError()
    return target_user_id


async def record_admin_action(
    audit: AuditLogRepository,
    actor: Identity,
    owner_id: int,
    action: str,
    resource_type: str,
    resource_id: int | None,
    now: datetime,
    details: dict[str, Any] | None = None,
) -> None:
    """Ghi nhật ký quản trị (F13.06) khi admin sửa/xóa dữ liệu của người khác; chủ sở hữu tự sửa thì bỏ qua.

    `details` chỉ chứa tóm tắt thay đổi (tên trường), không chứa nội dung riêng tư.
    """
    if owner_id == actor.user_id:
        return
    await audit.add(
        actor.user_id,
        action,
        resource_type,
        resource_id,
        {"target_user_id": owner_id, **(details or {})},
        now,
    )
