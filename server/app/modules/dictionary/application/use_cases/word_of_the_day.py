from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta, timezone

from app.core.clock import Clock
from app.core.errors import NotFoundError
from app.modules.dictionary.application.ports import DictionaryUnitOfWork
from app.modules.dictionary.domain.entities import WordOfTheDay
from app.modules.dictionary.domain.hsk import HSK_MAX, HSK_MIN

DEFAULT_LEVEL = 3
# Việt Nam không có giờ mùa hè nên dùng múi giờ cố định UTC+7 để xác định "hôm nay".
VIETNAM_TZ = timezone(timedelta(hours=7))


class WordOfTheDayUseCase:
    """Từ vựng trong ngày (thẻ ở trang Catalog): chọn ổn định theo ngày và trình độ HSK của người học."""

    def __init__(self, uow_factory: Callable[[], DictionaryUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, hsk_level: int | None) -> WordOfTheDay:
        level = hsk_level if hsk_level and HSK_MIN <= hsk_level <= HSK_MAX else DEFAULT_LEVEL
        day = self._clock.now().astimezone(VIETNAM_TZ).date()
        # Thử cấp của người học trước, rồi các cấp lân cận để không rỗng khi cấp đó thiếu dữ liệu.
        candidates = [level, *(lv for lv in range(HSK_MIN, HSK_MAX + 1) if lv != level)]
        async with self._uow_factory() as uow:
            for candidate in candidates:
                word = await uow.reader.word_of_the_day(candidate, day)
                if word is not None:
                    return word
        raise NotFoundError("Chưa có dữ liệu từ vựng HSK")
