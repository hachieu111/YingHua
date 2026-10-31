"""Bề mặt công khai của M13 cho module khác: quyền truy cập dữ liệu người khác, nhật ký quản trị (F13.07)
và cấu hình hệ thống (`SystemSettingsPort`, F13.05)."""

from __future__ import annotations

from app.modules.admin.application.ai_policy import (
    SystemSettingsAiPolicy,
    ai_note_ai_policy,
    grammar_ai_policy,
    mistake_review_ai_policy,
    quiz_ai_policy,
)
from app.modules.admin.application.dto import UserActivity
from app.modules.admin.application.ownership import record_admin_action, resolve_owner
from app.modules.admin.application.ports import AuditLogRepository, UserActivitySource
from app.modules.admin.application.system_settings import SystemSettingsPort
from app.modules.admin.application.use_cases.ensure_target_user import EnsureTargetUserUseCase
from app.modules.admin.domain.system_settings import SystemSettingsSnapshot

__all__ = [
    "AuditLogRepository",
    "EnsureTargetUserUseCase",
    "SystemSettingsAiPolicy",
    "SystemSettingsPort",
    "SystemSettingsSnapshot",
    "UserActivity",
    "UserActivitySource",
    "ai_note_ai_policy",
    "grammar_ai_policy",
    "mistake_review_ai_policy",
    "quiz_ai_policy",
    "record_admin_action",
    "resolve_owner",
]
