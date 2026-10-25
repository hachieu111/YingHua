from __future__ import annotations

from collections.abc import Callable

from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.vocab.application.dto import SavedSentencePage
from app.modules.vocab.application.ports import VocabUnitOfWork
from app.modules.vocab.application.sentence_views import build_sentence_items


class ListSavedSentencesUseCase:
    """F07.11 — Danh sách "Câu thoại đã lưu", mới nhất trước, có phân trang (US-NH-70).

    Chỉ trả câu của chủ sở hữu (người gọi, hoặc người đích khi quản trị viên truyền `owner_id`, F13.07).
    """

    def __init__(self, uow_factory: Callable[[], VocabUnitOfWork], pages: PageAccessPort) -> None:
        self._uow_factory = uow_factory
        self._pages = pages

    async def execute(
        self, identity: Identity, page: int, size: int, owner_id: int | None = None
    ) -> SavedSentencePage:
        owner = resolve_owner(identity, owner_id)
        async with self._uow_factory() as uow:
            sentences, total = await uow.sentences.page(owner, (page - 1) * size, size)
            items = await build_sentence_items(uow, self._pages, identity, sentences)
        return SavedSentencePage(items, total)
