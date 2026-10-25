"""Bộ hiện thực M05 mà tầng lắp ghép của module khác được dùng (chỉ ở tầng hạ tầng)."""

from __future__ import annotations

from app.modules.reader.infrastructure.repositories import SqlBubbleEditRepository
from app.modules.reader.infrastructure.uow import SqlReaderUnitOfWork

__all__ = ["SqlBubbleEditRepository", "SqlReaderUnitOfWork"]
