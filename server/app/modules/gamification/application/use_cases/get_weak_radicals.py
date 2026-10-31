from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.gamification.application.dto import WeakRadicalsView
from app.modules.gamification.application.ports import GamificationUnitOfWork
from app.modules.gamification.domain.minigame_rules import (
    NO_DATA_MESSAGE,
    WEAK_LOOKBACK_DAYS,
    WEAK_MAX_RADICALS,
    max_hsk_level,
    weak_radicals,
)


class GetWeakRadicalsUseCase:
    """F16.01 bước 1-2 - "Bộ thủ bạn hay quên": bộ thủ/thành phần xuất hiện nhiều trong các thẻ bị chấm Quên
    hoặc Khó 30 ngày gần đây (US-NH-81). Không dùng AI.

    Chưa bộ thủ nào đạt ngưỡng: đề xuất bộ thủ phổ biến của cấp HSK hiện tại kèm thông báo (`fallback`).
    """

    def __init__(self, uow_factory: Callable[[], GamificationUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity) -> WeakRadicalsView:
        since = self._clock.now() - timedelta(days=WEAK_LOOKBACK_DAYS)
        async with self._uow_factory() as uow:
            counts = await uow.chars.weak_char_counts(identity.user_id, since)
            weak = weak_radicals(counts, await uow.chars.hanzi_infos(counts))
            if weak:
                return WeakRadicalsView(weak, False, None)
            profile = await uow.users.profile(identity.user_id)
            common = await uow.chars.common_radicals(max_hsk_level(profile.hsk_level), WEAK_MAX_RADICALS)
        return WeakRadicalsView(common, True, NO_DATA_MESSAGE)
