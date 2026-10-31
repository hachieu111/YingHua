from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import timedelta

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.reader.application.access import load_readable_bubble
from app.modules.reader.application.dto import BubbleLookup
from app.modules.reader.application.ports import DictionaryLookup, ReaderUnitOfWork
from app.modules.reader.domain.entities import ConsumeOutcome, GuestQuota
from app.modules.reader.domain.errors import GuestLookupLimitReachedError, WordNotInBubbleError
from app.modules.reader.domain.rules import contains_word


class LookupBubbleWordUseCase:
    """F05.02, F05.03, F05.04 — Hover & Dịch: tra một từ trong bong bóng (US-NH-22, US-NH-23, US-KH-05).

    Người đã đăng nhập tra đầy đủ qua M06 (và được ghi lịch sử tra). Khách chỉ nhận phần cơ bản và bị giới
    hạn `guest_limit` lượt mỗi phiên ẩn danh; hết lượt thì không trả kết quả (429, mời đăng ký). Bộ đếm
    tăng nguyên tử ở máy chủ nên gửi đồng thời cũng không vượt hạn mức.
    """

    def __init__(
        self,
        uow_factory: Callable[[], ReaderUnitOfWork],
        pages: PageAccessPort,
        dictionary: DictionaryLookup,
        clock: Clock,
        guest_limit: int,
        guest_session_ttl: timedelta,
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._dictionary = dictionary
        self._clock = clock
        self._guest_limit = guest_limit
        self._guest_ttl = guest_session_ttl

    async def execute(
        self, identity: Identity | None, guest_session_id: uuid.UUID | None, bubble_id: int, word: str
    ) -> BubbleLookup:
        async with self._uow_factory() as uow:
            bubble = await load_readable_bubble(uow, self._pages, identity, bubble_id)
        if not contains_word(bubble.text_zh, word):
            raise WordNotInBubbleError()
        guest = await self._consume_guest_quota(guest_session_id) if identity is None else None
        result = await self._dictionary.lookup(word, identity, bubble_id)
        return BubbleLookup(bubble_id=bubble_id, word=word, result=result, guest=guest)

    async def _consume_guest_quota(self, session_id: uuid.UUID | None) -> GuestQuota:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            outcome, used = (
                await uow.guests.consume(session_id, self._guest_limit, now)
                if session_id is not None
                else (ConsumeOutcome.UNKNOWN, 0)
            )
            if outcome is ConsumeOutcome.UNKNOWN:
                session_id = await uow.guests.create(now, now + self._guest_ttl, used=1)
                used = 1
            await uow.commit()
        assert session_id is not None
        if outcome is ConsumeOutcome.LIMIT_REACHED:
            raise GuestLookupLimitReachedError(
                details={"limit": self._guest_limit, "remaining": 0, "login_required": True}
            )
        return GuestQuota(session_id=str(session_id), limit=self._guest_limit, used=used)
