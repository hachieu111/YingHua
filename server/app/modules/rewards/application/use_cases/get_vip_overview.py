from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.admin.application.public import SystemSettingsPort
from app.modules.auth.application.public import Identity
from app.modules.rewards.application.dto import AiLimits, VipOverview
from app.modules.rewards.application.ports import RewardsUnitOfWork
from app.modules.rewards.application.views import vip_status_of
from app.modules.rewards.domain.rules import effective_ai_limit


class GetVipOverviewUseCase:
    """F17.03 - `GET /vip/me`: có đang VIP không, hạn, quyền lợi và hạn mức AI hiệu lực (US-NH-94).

    Trạng thái tính theo thời điểm gọi, không phụ thuộc tác vụ nền (VIP hết hạn giữa phiên là hết ngay).
    """

    def __init__(
        self, uow_factory: Callable[[], RewardsUnitOfWork], settings: SystemSettingsPort, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._settings = settings
        self._clock = clock

    async def execute(self, identity: Identity) -> VipOverview:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            status = vip_status_of(await uow.wallets.get_wallet(identity.user_id), now)
            unlocks = await uow.unlocks.list_for_user(identity.user_id)
        s = await self._settings.snapshot()
        vip = status.is_active
        limits = AiLimits(
            quiz_daily_llm_limit=effective_ai_limit(vip, s.quiz_daily_llm_limit, s.vip_quiz_daily_llm_limit),
            ai_note_daily_limit=effective_ai_limit(vip, s.ai_note_daily_limit, s.vip_ai_note_daily_limit),
            grammar_daily_limit=effective_ai_limit(vip, s.grammar_daily_limit, s.vip_grammar_daily_limit),
            mistake_review_daily_limit=effective_ai_limit(
                vip, s.mistake_review_daily_limit, s.vip_mistake_review_daily_limit
            ),
        )
        return VipOverview(status, limits, vip, vip, len(unlocks))
