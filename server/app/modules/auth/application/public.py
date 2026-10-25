"""Bề mặt công khai của M01 cho các module khác (kiểu, port, danh tính). Module khác chỉ import từ đây."""

from __future__ import annotations

from app.modules.auth.application.dto import Identity
from app.modules.auth.application.ports import SessionRepository, UserRepository
from app.modules.auth.application.use_cases.purge_expired_sessions import (
    PurgeExpiredSessionsUseCase,
    SessionPurgeReport,
)
from app.modules.auth.domain.entities import Role, User, UserStatus

__all__ = [
    "Identity",
    "PurgeExpiredSessionsUseCase",
    "Role",
    "SessionPurgeReport",
    "SessionRepository",
    "User",
    "UserRepository",
    "UserStatus",
]
