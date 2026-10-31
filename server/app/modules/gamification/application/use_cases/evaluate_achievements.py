from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from app.modules.gamification.application.achievement_engine import AchievementEngine
from app.modules.gamification.application.dto import EvaluateReport, Notice
from app.modules.gamification.application.ports import GamificationUnitOfWork, NoticeSender

logger = logging.getLogger(__name__)

ACTIVE_WINDOW = timedelta(
    hours=25
)  # "người có hoạt động trong ngày", dư 1 giờ để không hụt khi lịch chạy trễ
BATCH_SIZE = 200
MAX_USERS_PER_RUN = 2000


class EvaluateAchievementsUseCase:
    """F16.11 - Quét nền mỗi 60 phút: đánh giá mọi huy hiệu theo luật cho người có hoạt động trong ngày, bắt
    các chỉ số không sinh XP (vd. số bong bóng đã tra) (US-NH-91).

    Mỗi người một giao dịch riêng; lỗi của một người chỉ ghi log và bỏ qua, lần chạy sau tính lại.
    Thông báo gửi sau khi giao dịch của người đó đã lưu.
    """

    def __init__(self, uow_factory: Callable[[], GamificationUnitOfWork], notices: NoticeSender) -> None:
        self._uow_factory = uow_factory
        self._notices = notices

    async def execute(self, now: datetime) -> EvaluateReport:
        scanned = unlocked = failed = 0
        after = 0
        since = now - ACTIVE_WINDOW
        while scanned < MAX_USERS_PER_RUN:
            async with self._uow_factory() as uow:
                batch = await uow.metrics.active_users(since, after, BATCH_SIZE)
            if not batch:
                break
            for user_id in batch:
                scanned += 1
                try:
                    unlocked += await self._evaluate_user(user_id, now)
                except Exception:
                    failed += 1
                    logger.exception("Không đánh giá được huy hiệu của một người dùng")
            after = batch[-1]
        return EvaluateReport(scanned, unlocked, failed)

    async def _evaluate_user(self, user_id: int, now: datetime) -> int:
        pending: list[Notice] = []
        async with self._uow_factory() as uow:
            profile = await uow.users.profile(user_id)
            upgraded = await AchievementEngine(uow).evaluate(user_id, profile.timezone, None, now, pending)
            await uow.commit()
        for notice in pending:
            await self._notices.send(notice)
        return upgraded
