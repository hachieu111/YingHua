"""Bộ hiện thực mà module khác được dùng khi lắp giao dịch của chính nó (chỉ ở tầng hạ tầng)."""

from __future__ import annotations

from app.modules.admin.infrastructure.repositories import SqlAuditLogRepository

__all__ = ["SqlAuditLogRepository"]
