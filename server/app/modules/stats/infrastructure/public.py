"""Hiện thực M12 mà tầng lắp ghép của module khác được dùng."""

from __future__ import annotations

from app.modules.stats.infrastructure.recorder import SqlActivityRecorder
from app.modules.stats.infrastructure.uow import SqlStatsUnitOfWork

__all__ = ["SqlActivityRecorder", "SqlStatsUnitOfWork"]
