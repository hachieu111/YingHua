"""Chính sách dùng LLM đọc từ cấu hình hệ thống do quản trị đặt (F13.05).

Hiện thực port `app.core.ai_policy.AiPolicy` (theo cấu trúc, không import) để reader (F05.09) và quiz (F09.10)
lấy công tắc LLM và hạn mức ngày mà không biết gì về nội bộ M13. Đọc qua `SystemSettingsPort` mỗi lần hỏi nên
quản trị đổi trong `PATCH /admin/system-settings` có hiệu lực sau tối đa vài giây đệm.
"""

from __future__ import annotations

from collections.abc import Callable

from app.modules.admin.application.system_settings import SystemSettingsPort
from app.modules.admin.domain.system_settings import SystemSettingsSnapshot


class SystemSettingsAiPolicy:
    def __init__(
        self, settings: SystemSettingsPort, limit_of: Callable[[SystemSettingsSnapshot], int]
    ) -> None:
        self._settings = settings
        self._limit_of = limit_of

    async def llm_enabled(self) -> bool:
        return (await self._settings.snapshot()).llm_enabled

    async def daily_limit(self) -> int:
        return self._limit_of(await self._settings.snapshot())


def grammar_ai_policy(settings: SystemSettingsPort) -> SystemSettingsAiPolicy:
    """Phân tích ngữ pháp câu thoại (F05.09)."""
    return SystemSettingsAiPolicy(settings, lambda s: s.grammar_daily_limit)


def mistake_review_ai_policy(settings: SystemSettingsPort) -> SystemSettingsAiPolicy:
    """Giải thích lỗi sai trong bài kiểm tra (F09.10)."""
    return SystemSettingsAiPolicy(settings, lambda s: s.mistake_review_daily_limit)
