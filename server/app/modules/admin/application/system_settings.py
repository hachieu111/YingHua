"""Đọc cấu hình hệ thống có bộ đệm ngắn trong tiến trình (F13.05).

Đây là cổng công khai `SystemSettingsPort` mà module khác (M09 quiz, M08 review, M11 tts, M05 reader...)
dùng để đọc công tắc và hạn mức thay cho các giá trị tạm trong `Settings`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import timedelta
from typing import Any, Protocol

from app.core.clock import Clock
from app.core.config import Settings
from app.core.ttl_cache import TtlCache
from app.modules.admin.domain.errors import InvalidSettingValueError
from app.modules.admin.domain.system_settings import (
    SETTING_SPECS,
    SystemSettingsSnapshot,
    validate_setting,
)

log = logging.getLogger(__name__)

# Bộ đệm ngắn để không truy vấn CSDL ở mỗi yêu cầu; ghi qua API quản trị xóa bộ đệm ngay (có hiệu lực ngay).
SYSTEM_SETTINGS_CACHE_SECONDS = 5


class SystemSettingsPort(Protocol):
    """Cổng công khai: giá trị hiệu lực của mọi khóa cấu hình hệ thống."""

    async def snapshot(self) -> SystemSettingsSnapshot: ...


class SystemSettingsSource(Protocol):
    """Nguồn đọc thô các khóa đã đặt trong CSDL (mỗi lần gọi một giao dịch riêng)."""

    async def load_all(self) -> dict[str, Any]: ...


def defaults_from_settings(settings: Settings) -> SystemSettingsSnapshot:
    """Mặc định khi khóa chưa có trong CSDL."""
    return SystemSettingsSnapshot(
        llm_enabled=settings.llm_enabled,
        tts_enabled=settings.tts_enabled,
        quiz_daily_llm_limit=settings.quiz_daily_llm_limit,
        ai_note_daily_limit=settings.ai_note_daily_limit,
        grammar_daily_limit=settings.grammar_daily_limit,
        mistake_review_daily_limit=settings.mistake_review_daily_limit,
        vip_quiz_daily_llm_limit=settings.vip_quiz_daily_llm_limit,
        vip_ai_note_daily_limit=settings.vip_ai_note_daily_limit,
        vip_grammar_daily_limit=settings.vip_grammar_daily_limit,
        vip_mistake_review_daily_limit=settings.vip_mistake_review_daily_limit,
        maintenance_mode=False,
        auto_moderation_enabled=True,
        ocr_on_upload_enabled=True,
        admin_notifications_enabled=True,
        sample_page_id=None,
    )


def merge_settings(
    defaults: SystemSettingsSnapshot, stored: dict[str, Any]
) -> tuple[SystemSettingsSnapshot, list[str]]:
    """Gộp giá trị trong CSDL lên mặc định; giá trị hỏng bị bỏ qua (ghi cảnh báo).

    Trả (kết quả, khóa đã đặt).
    """
    values = defaults.as_dict()
    overridden: list[str] = []
    for key in SETTING_SPECS:
        if key not in stored:
            continue
        try:
            values[key] = validate_setting(key, stored[key])
        except InvalidSettingValueError:
            log.warning("Bỏ qua giá trị cấu hình hỏng trong CSDL: key=%s", key)
            continue
        overridden.append(key)
    return SystemSettingsSnapshot(**values), overridden


class CachedSystemSettings:
    """Hiện thực `SystemSettingsPort`: mặc định từ `Settings` + giá trị trong CSDL, đệm vài giây."""

    def __init__(
        self,
        source_factory: Callable[[], SystemSettingsSource],
        defaults: SystemSettingsSnapshot,
        clock: Clock,
        ttl_seconds: int = SYSTEM_SETTINGS_CACHE_SECONDS,
    ) -> None:
        self._source_factory = source_factory
        self._defaults = defaults
        self._ttl = timedelta(seconds=ttl_seconds)
        self._cache: TtlCache[SystemSettingsSnapshot] = TtlCache(clock)

    @property
    def defaults(self) -> SystemSettingsSnapshot:
        return self._defaults

    async def snapshot(self) -> SystemSettingsSnapshot:
        cached = self._cache.get()
        if cached is not None:
            return cached
        merged, _ = merge_settings(self._defaults, await self._source_factory().load_all())
        self._cache.set(merged, self._ttl)
        return merged

    async def overridden_keys(self) -> list[str]:
        """Khóa đã đặt trong CSDL (không đệm: chỉ màn hình quản trị gọi)."""
        _, overridden = merge_settings(self._defaults, await self._source_factory().load_all())
        return overridden

    def invalidate(self) -> None:
        self._cache.clear()
