from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.suggestions.application.analysis import analyze_chapter, fold_reduplicated
from app.modules.suggestions.application.ports import (
    ChapterSource,
    SuggestionUnitOfWork,
    TermHints,
    WordSaver,
)
from app.modules.suggestions.domain.errors import SuggestionNotFoundError
from app.modules.suggestions.domain.rules import normalize_term
from app.modules.vocab.application.public import SaveWordCommand, SaveWordResult

SUGGESTION_ORIGIN = "suggestion"


class AcceptSuggestionUseCase:
    """F10.02 — Nhận gợi ý vào sổ tay như thao tác lưu thông thường (US-NH-52).

    Lấy bong bóng của lần xuất hiện đầu tiên của từ trong chương làm ngữ cảnh rồi gọi `SaveWordUseCase`
    (F07.01); từ đã có thì áp dụng F07.02 (thêm ngữ cảnh hoặc 409). Lưu lỗi thì từ vẫn ở danh sách gợi ý.
    Từ không xuất hiện trong chương → 404.
    """

    def __init__(
        self,
        uow_factory: Callable[[], SuggestionUnitOfWork],
        chapters: ChapterSource,
        saver: WordSaver,
        hints: TermHints,
    ) -> None:
        self._hints = hints
        self._uow_factory = uow_factory
        self._chapters = chapters
        self._saver = saver

    async def execute(self, identity: Identity, chapter_id: int, term: str) -> SaveWordResult:
        word = normalize_term(term)
        async with self._uow_factory() as uow:
            analysis = await analyze_chapter(self._chapters, uow, identity, chapter_id)
        first = (await fold_reduplicated(analysis.stats, self._hints)).get(word)
        if first is None:
            raise SuggestionNotFoundError()
        return await self._saver.execute(
            identity, SaveWordCommand(word, SUGGESTION_ORIGIN, first.bubble_id, first.page_id)
        )
