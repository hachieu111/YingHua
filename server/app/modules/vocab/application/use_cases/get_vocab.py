from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.vocab.application.access import load_entry
from app.modules.vocab.application.dto import VocabDetail
from app.modules.vocab.application.ports import TermDictionary, VocabUnitOfWork
from app.modules.vocab.application.views import build_detail


class GetVocabUseCase:
    """F07.05, F07.07, F08.04 — Chi tiết một từ: mọi ngữ cảnh (ảnh, câu, nguồn truyện), ba thẻ, ghi chú.

    Từ của người khác trả như không tồn tại (404), trừ quản trị viên xem qua `owner_id` (F13.07).
    Ngữ cảnh có trang nguồn đã xóa hoặc hết quyền đọc vẫn hiện ảnh/câu đã lưu nhưng `source` rỗng.
    """

    def __init__(
        self,
        uow_factory: Callable[[], VocabUnitOfWork],
        pages: PageAccessPort,
        dictionary: TermDictionary,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._dictionary = dictionary
        self._clock = clock

    async def execute(self, identity: Identity, entry_id: int, owner_id: int | None = None) -> VocabDetail:
        owner = resolve_owner(identity, owner_id)
        async with self._uow_factory() as uow:
            entry = await load_entry(uow, owner, entry_id)
            return await build_detail(uow, self._pages, self._dictionary, identity, entry, self._clock.now())
