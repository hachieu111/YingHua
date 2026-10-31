"""Hạn mức AI theo VIP (F17.04): bọc chính sách đọc cấu hình của M13.

`VipAwareAiPolicy` hiện thực port `app.core.ai_policy.AiPolicy`. Không VIP dùng hạn mức thường; đang VIP dùng
max(hạn mức VIP, hạn mức thường). Công tắc LLM giữ nguyên: tắt LLM áp dụng cho mọi người. Lượt đã dùng trong
ngày tính chung (cách đếm của từng tính năng không đổi).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from app.core.ai_policy import AiPolicies, AiPolicy
from app.core.clock import Clock
from app.modules.admin.application.public import (
    SystemSettingsPort,
    SystemSettingsSnapshot,
    ai_note_ai_policy,
    grammar_ai_policy,
    mistake_review_ai_policy,
    quiz_ai_policy,
)
from app.modules.rewards.domain.rules import effective_ai_limit

logger = logging.getLogger(__name__)


class VipStatusReader(Protocol):
    async def is_vip(self, user_id: int, now: datetime) -> bool: ...


class VipAwareAiPolicy:
    def __init__(
        self,
        base: AiPolicy,
        settings: SystemSettingsPort,
        vip_limit_of: Callable[[SystemSettingsSnapshot], int],
        vip: VipStatusReader,
        clock: Clock,
    ) -> None:
        self._base = base
        self._settings = settings
        self._vip_limit_of = vip_limit_of
        self._vip = vip
        self._clock = clock

    async def llm_enabled(self) -> bool:
        return await self._base.llm_enabled()

    async def daily_limit(self, user_id: int) -> int:
        normal = await self._base.daily_limit(user_id)
        try:
            if not await self._vip.is_vip(user_id, self._clock.now()):
                return normal
            vip_limit = self._vip_limit_of(await self._settings.snapshot())
        except Exception:
            # Không đọc được trạng thái VIP thì dùng hạn mức thường, không chặn tính năng (F17.04).
            logger.warning("Không đọc được trạng thái VIP, dùng hạn mức AI thường", exc_info=True)
            return normal
        return effective_ai_limit(True, normal, vip_limit)


def build_ai_policies(settings: SystemSettingsPort, vip: VipStatusReader, clock: Clock) -> AiPolicies:
    """Lắp chính sách VIP cho bốn tính năng LLM; `container.py` gọi một lần."""
    return AiPolicies(
        quiz=VipAwareAiPolicy(
            quiz_ai_policy(settings), settings, lambda s: s.vip_quiz_daily_llm_limit, vip, clock
        ),
        ai_note=VipAwareAiPolicy(
            ai_note_ai_policy(settings), settings, lambda s: s.vip_ai_note_daily_limit, vip, clock
        ),
        grammar=VipAwareAiPolicy(
            grammar_ai_policy(settings), settings, lambda s: s.vip_grammar_daily_limit, vip, clock
        ),
        mistake_review=VipAwareAiPolicy(
            mistake_review_ai_policy(settings),
            settings,
            lambda s: s.vip_mistake_review_daily_limit,
            vip,
            clock,
        ),
    )
