from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.vocab.application.dto import ListVocabQuery
from app.modules.vocab.application.filters import build_vocab_filter
from app.modules.vocab.application.ports import VocabUnitOfWork
from app.modules.vocab.domain.entities import VocabEntry
from app.modules.vocab.domain.export import (
    EXPORT_PAGE_SIZE,
    MAX_EXPORT_ROWS,
    ExportFile,
    ExportTooLargeError,
    parse_export_format,
    render_export,
)


class ExportVocabUseCase:
    """F07.08 — Xuất sổ tay ra CSV (UTF-8 có BOM) hoặc tệp nhập được vào Anki (US-NH-60).

    Xuất đúng các từ thỏa bộ lọc đang áp dụng (cùng bộ lọc với F07.07); không có bộ lọc thì xuất toàn bộ.
    Chỉ dữ liệu của chủ sở hữu (quản trị viên xuất của người khác qua `owner_id`, F13.07). Sổ tay trống/không
    khớp bộ lọc → `VOCAB_EXPORT_EMPTY` ("Sổ tay chưa có từ để xuất"); quá 5000 từ → `VOCAB_EXPORT_TOO_LARGE`.
    Không xuất ảnh ngữ cảnh.
    """

    def __init__(
        self, uow_factory: Callable[[], VocabUnitOfWork], pages: PageAccessPort, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._clock = clock

    async def execute(
        self, identity: Identity, fmt: str, query: ListVocabQuery, owner_id: int | None = None
    ) -> ExportFile:
        export_format = parse_export_format(fmt)
        owner = resolve_owner(identity, owner_id)
        now = self._clock.now()
        flt = await build_vocab_filter(self._pages, query, owner, now)
        entries: list[VocabEntry] = []
        async with self._uow_factory() as uow:
            while True:
                batch, total = await uow.entries.search(flt, len(entries), EXPORT_PAGE_SIZE)
                if total > MAX_EXPORT_ROWS:
                    raise ExportTooLargeError()
                entries.extend(batch)
                if not batch or len(entries) >= total:
                    break
        return render_export(export_format, entries, now.date())
