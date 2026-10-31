from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from app.modules.gamification.application.ports import GamificationUnitOfWork
from app.modules.gamification.domain.minigame_rules import (
    ROUND_PURGE_BATCH_SIZE,
    ROUND_PURGE_MAX_BATCHES,
    ROUND_RETENTION_DAYS,
)


class PurgeMinigameRoundsUseCase:
    """F16.01, F15.03 - Dọn lượt mini-game đã phát quá `ROUND_RETENTION_DAYS` ngày (đã nộp hay chưa).

    Chỉ lọc theo `issued_at`, xóa theo lô có LIMIT, mỗi lô một giao dịch; không đụng `minigame_sessions`
    (lịch sử ván đã chơi). Trả số dòng đã xóa.
    """

    def __init__(self, uow_factory: Callable[[], GamificationUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, now: datetime) -> int:
        cutoff = now - timedelta(days=ROUND_RETENTION_DAYS)
        total = 0
        for _ in range(ROUND_PURGE_MAX_BATCHES):
            async with self._uow_factory() as uow:
                deleted = await uow.minigames.purge_rounds_before(cutoff, ROUND_PURGE_BATCH_SIZE)
                await uow.commit()
            total += deleted
            if deleted < ROUND_PURGE_BATCH_SIZE:
                break
        return total
