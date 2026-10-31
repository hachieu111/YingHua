"""Hiện thực M16 mà tầng lắp ghép (container, worker) và Unit of Work của module nguồn được dùng."""

from __future__ import annotations

from app.modules.gamification.infrastructure.learning_events import SqlLearningEvents
from app.modules.gamification.infrastructure.notice_sender import (
    NotificationsNoticeSender,
    build_notice_sender,
)
from app.modules.gamification.infrastructure.store import SqlGamificationUnitOfWork

__all__ = [
    "NotificationsNoticeSender",
    "SqlGamificationUnitOfWork",
    "SqlLearningEvents",
    "build_notice_sender",
]
