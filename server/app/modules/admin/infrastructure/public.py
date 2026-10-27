"""Bộ hiện thực mà module khác được dùng khi lắp giao dịch của chính nó (chỉ ở tầng hạ tầng)."""

from __future__ import annotations

from app.modules.admin.infrastructure.repositories import SqlAuditLogRepository
from app.modules.admin.infrastructure.system_settings_repository import SqlSystemSettingsSource

__all__ = ["SqlAuditLogRepository", "SqlSystemSettingsSource"]
