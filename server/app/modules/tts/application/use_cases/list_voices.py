from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from app.core.clock import Clock
from app.core.errors import ExternalServiceError
from app.core.ttl_cache import TtlCache
from app.modules.tts.application.ports import VoiceCatalog
from app.modules.tts.domain.voices import DEFAULT_VOICES, FAILURE_TTL, VOICES_TTL, VoiceInfo

logger = logging.getLogger(__name__)

SOURCE_SERVICE = "service"
SOURCE_DEFAULT = "default"


@dataclass(frozen=True, slots=True)
class VoiceList:
    voices: list[VoiceInfo]
    source: str  # service: lấy từ dịch vụ; default: danh sách có sẵn trong mã khi dịch vụ lỗi


class ListVoicesUseCase:
    """F11.03 — Danh sách giọng tiếng Trung khả dụng cho trang Cài đặt (US-NH-55).

    Lấy từ dịch vụ TTS và lưu đệm trong bộ nhớ (`VOICES_TTL`). Dịch vụ lỗi hoặc không có giọng zh-* nào thì
    trả danh sách mặc định và nhớ tạm `FAILURE_TTL` để không gọi dồn dập; không bao giờ trả lỗi 503 vì trang
    Cài đặt vẫn phải chọn được giọng. Sự kiện dự phòng ghi mức cảnh báo.
    """

    def __init__(self, catalog: VoiceCatalog, cache: TtlCache[VoiceList], clock: Clock) -> None:
        self._catalog = catalog
        self._cache = cache
        self._clock = clock

    async def execute(self) -> VoiceList:
        cached = self._cache.get()
        if cached is not None:
            return cached
        try:
            voices = await self._catalog.list_voices()
        except ExternalServiceError as exc:
            logger.warning("Không lấy được danh sách giọng TTS (%s), dùng danh sách mặc định", exc.code)
            return self._remember(VoiceList(list(DEFAULT_VOICES), SOURCE_DEFAULT), FAILURE_TTL)
        if not voices:
            logger.warning("Dịch vụ TTS không trả giọng tiếng Trung nào, dùng danh sách mặc định")
            return self._remember(VoiceList(list(DEFAULT_VOICES), SOURCE_DEFAULT), FAILURE_TTL)
        return self._remember(VoiceList(voices, SOURCE_SERVICE), VOICES_TTL)

    def _remember(self, result: VoiceList, ttl: timedelta) -> VoiceList:
        self._cache.set(result, ttl)
        return result
