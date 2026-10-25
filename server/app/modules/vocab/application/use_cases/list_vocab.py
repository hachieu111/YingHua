from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.vocab.application.dto import ListVocabQuery, VocabListPage
from app.modules.vocab.application.ports import TermDictionary, VocabUnitOfWork
from app.modules.vocab.application.views import build_list_items
from app.modules.vocab.domain.entities import VocabFilter
from app.modules.vocab.domain.rules import parse_hsk_filter, parse_status


class ListVocabUseCase:
    """F07.07 — Xem và lọc sổ tay theo cấp HSK, trạng thái, từ khóa, dấu sao, truyện (US-NH-37).

    `due=true/false` ("Cần ôn lại") theo đúng quy tắc của GET /cards/due: từ còn "Đang học" và có thẻ không
    tạm ngưng với `due_at <= now`; lọc ở SQL nên `total` đúng. Các bộ lọc ghép bằng "và"; chỉ trả dữ liệu
    của chủ sở hữu (người gọi, hoặc người đích khi quản trị viên truyền `owner_id`, F13.07); chia trang.
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

    async def execute(
        self, identity: Identity, query: ListVocabQuery, owner_id: int | None = None
    ) -> VocabListPage:
        owner = resolve_owner(identity, owner_id)
        now = self._clock.now()
        hsk_level, hsk_none = parse_hsk_filter(query.hsk)
        page_ids = await self._pages.page_ids_of_series(query.series_id) if query.series_id else None
        flt = VocabFilter(
            user_id=owner,
            status=parse_status(query.status) if query.status else None,
            hsk_level=hsk_level,
            hsk_none=hsk_none,
            query=(query.query or "").strip() or None,
            starred=query.starred,
            page_ids=page_ids,
            due=query.due,
            now=now,
        )
        async with self._uow_factory() as uow:
            entries, total = await uow.entries.search(flt, (query.page - 1) * query.size, query.size)
            items = await build_list_items(uow, self._dictionary, owner, entries, now)
        return VocabListPage(items, total)
