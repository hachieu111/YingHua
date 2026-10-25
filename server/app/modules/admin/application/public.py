"""Bề mặt công khai của M13 cho module khác: quyền truy cập dữ liệu người khác, nhật ký quản trị (F13.07)."""

from __future__ import annotations

from app.modules.admin.application.dto import UserActivity
from app.modules.admin.application.ownership import record_admin_action, resolve_owner
from app.modules.admin.application.ports import AuditLogRepository, UserActivitySource
from app.modules.admin.application.use_cases.ensure_target_user import EnsureTargetUserUseCase

__all__ = [
    "AuditLogRepository",
    "EnsureTargetUserUseCase",
    "UserActivity",
    "UserActivitySource",
    "record_admin_action",
    "resolve_owner",
]
