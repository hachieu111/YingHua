"""Hiện thực `LearningEventPort` (core) cho M16: gắn vào Unit of Work của module nguồn, chung phiên."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.learning_events import LearningEvent, LearningSignal
from app.modules.gamification.application.achievement_engine import AchievementEngine
from app.modules.gamification.application.dto import Notice
from app.modules.gamification.application.recorder import EventRecorder
from app.modules.gamification.domain.achievement_rules import SIGNAL_METRICS
from app.modules.gamification.domain.entities import AchievementMetric
from app.modules.gamification.infrastructure.notice_sender import build_notice_sender_for_session
from app.modules.gamification.infrastructure.store import SqlGamificationStore, SqlGamificationUnitOfWork

logger = logging.getLogger(__name__)


class SqlLearningEvents:
    """Ghi XP và thưởng phụ trong cùng giao dịch với hành động học; thông báo xếp hàng, gửi sau khi commit.

    Lỗi CSDL khi ghi làm hủy cả giao dịch của hành động (không có trạng thái "đã lưu từ nhưng mất XP").
    Tín hiệu chỉ số huy hiệu (`signal`) thì khác: đánh giá SAU commit, trong giao dịch riêng; lỗi chỉ ghi
    log WARNING và tác vụ nền 60 phút bù lại, nên không bao giờ làm hỏng hành động chính (như đường hover).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._recorder = EventRecorder(SqlGamificationStore(session))
        self._pending: list[Notice] = []
        self._signals: dict[int, set[AchievementMetric]] = {}
        self._last_at: datetime | None = None

    async def record(self, event: LearningEvent) -> int:
        self._last_at = event.at
        return await self._recorder.record(event, self._pending)

    async def signal(self, user_id: int, signal: LearningSignal, at: datetime) -> None:
        self._last_at = at
        self._signals.setdefault(user_id, set()).update(SIGNAL_METRICS[signal])

    async def after_commit(self) -> None:
        pending, self._pending = self._pending, []
        signals, self._signals = self._signals, {}
        if self._last_at is None:
            return
        at = self._last_at
        for user_id, metrics in signals.items():
            try:
                pending.extend(await self._evaluate(user_id, frozenset(metrics), at))
            except Exception:
                logger.warning("Không đánh giá được huy hiệu ngay cho user_id=%s", user_id, exc_info=True)
        if not pending:
            return
        sender = build_notice_sender_for_session(self._session, at)
        for notice in pending:
            await sender.send(notice)

    async def _evaluate(
        self, user_id: int, metrics: frozenset[AchievementMetric], at: datetime
    ) -> list[Notice]:
        assert self._session.bind is not None
        factory = async_sessionmaker(self._session.bind, expire_on_commit=False)
        notices: list[Notice] = []
        async with SqlGamificationUnitOfWork(factory) as uow:
            profile = await uow.users.profile(user_id)
            await AchievementEngine(uow).evaluate(user_id, profile.timezone, metrics, at, notices)
            await uow.commit()
        return notices
