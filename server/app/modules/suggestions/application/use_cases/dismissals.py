from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.glosses import short_meaning
from app.modules.auth.application.public import Identity
from app.modules.suggestions.application.dto import DismissedItem, DismissedPage
from app.modules.suggestions.application.ports import SuggestionUnitOfWork, TermHints
from app.modules.suggestions.domain.rules import normalize_term


class DismissSuggestionUseCase:
    """F10.03 — Bỏ qua một từ gợi ý: không gợi ý lại ở mọi chương cho tới khi khôi phục (US-NH-52).

    Idempotent: bỏ qua lần hai không lỗi.
    """

    def __init__(self, uow_factory: Callable[[], SuggestionUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, term: str) -> None:
        word = normalize_term(term)
        async with self._uow_factory() as uow:
            await uow.dismissed.add(identity.user_id, word, self._clock.now())
            await uow.commit()


class RestoreSuggestionUseCase:
    """F10.03 — Khôi phục từ đã bỏ qua để được gợi ý lại; từ không có trong danh sách thì bỏ qua."""

    def __init__(self, uow_factory: Callable[[], SuggestionUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity, term: str) -> None:
        word = normalize_term(term)
        async with self._uow_factory() as uow:
            await uow.dismissed.remove(identity.user_id, word)
            await uow.commit()


class ListDismissedUseCase:
    """F10.03 — Mục "Đã bỏ qua": từ đã bỏ qua kèm pinyin, nghĩa ngắn, cấp HSK, mới nhất trước (US-NH-52)."""

    def __init__(self, uow_factory: Callable[[], SuggestionUnitOfWork], hints: TermHints) -> None:
        self._uow_factory = uow_factory
        self._hints = hints

    async def execute(self, identity: Identity, page: int, size: int) -> DismissedPage:
        async with self._uow_factory() as uow:
            rows, total = await uow.dismissed.page(identity.user_id, (page - 1) * size, size)
        terms = [r.term for r in rows]
        briefs = await self._hints.briefs(terms)
        levels = await self._hints.hsk_levels(terms)
        items = [
            DismissedItem(
                r,
                briefs[r.term].pinyin if r.term in briefs else None,
                (short_meaning(briefs[r.term].meaning_vi) or None) if r.term in briefs else None,
                levels.get(r.term),
            )
            for r in rows
        ]
        return DismissedPage(items, total)
