from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccess, PageAccessPort
from app.modules.vocab.application.dto import SavedSentenceItem, SaveSentenceCommand
from app.modules.vocab.application.ports import VocabUnitOfWork
from app.modules.vocab.application.sentence_views import build_sentence_items
from app.modules.vocab.domain.entities import NewSavedSentence
from app.modules.vocab.domain.errors import (
    BubbleNotFoundError,
    EmptyBubbleTextError,
    SentenceAlreadySavedError,
)
from app.modules.vocab.domain.rules import clean_note, source_label


class SaveSentenceUseCase:
    """F07.11 — Lưu câu thoại (một bong bóng) để xem và nghe lại sau (US-NH-70).

    Lưu BẢN SAO văn bản: câu Trung, bản dịch (bản sửa cá nhân F05.05 nếu có, không thì bản dịch tự động) và
    nhãn nguồn, nên vẫn còn khi trang hoặc bong bóng bị xóa. Mỗi bong bóng chỉ lưu một lần mỗi người: lưu lại
    → `SentenceAlreadySavedError` (409, kèm `details.saved_sentence_id`). Bong bóng không đọc được → 404.
    """

    def __init__(
        self,
        uow_factory: Callable[[], VocabUnitOfWork],
        pages: PageAccessPort,
        clock: Clock,
        note_max_chars: int,
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._clock = clock
        self._note_max_chars = note_max_chars

    async def execute(self, identity: Identity, command: SaveSentenceCommand) -> SavedSentenceItem:
        note = clean_note(command.note, self._note_max_chars)
        user_id = identity.user_id
        async with self._uow_factory() as uow:
            bubble = await uow.bubbles.get(command.bubble_id)
            if bubble is None or not await self._pages.can_read_translation(identity, bubble.translation_id):
                raise BubbleNotFoundError()
            sentence_zh = bubble.text_zh.strip()
            if not sentence_zh:
                raise EmptyBubbleTextError()
            existing = await uow.sentences.get_by_bubble(user_id, bubble.id)
            if existing is not None:
                raise SentenceAlreadySavedError(details={"saved_sentence_id": existing.id})
            page = await self._find_page(identity, command.page_id, bubble.translation_id)
            edits = await uow.edits.get_many(user_id, [bubble.id])
            created = await uow.sentences.add_if_absent(
                NewSavedSentence(
                    user_id=user_id,
                    sentence_zh=sentence_zh,
                    created_at=self._clock.now(),
                    bubble_id=bubble.id,
                    page_id=page.page_id if page else None,
                    sentence_vi=edits.get(bubble.id) or bubble.text_vi,
                    source_label=(
                        source_label(page.series_title, page.chapter_number, page.page_no) if page else None
                    ),
                    note=note,
                )
            )
            if created is None:  # yêu cầu đồng thời khác vừa lưu cùng bong bóng
                raced = await uow.sentences.get_by_bubble(user_id, bubble.id)
                raise SentenceAlreadySavedError(details={"saved_sentence_id": raced.id if raced else None})
            await uow.commit()
            return (await build_sentence_items(uow, self._pages, identity, [created]))[0]

    async def _find_page(
        self, identity: Identity, page_id: int | None, translation_id: int
    ) -> PageAccess | None:
        if page_id is None:
            return await self._pages.readable_page_for_translation(identity, translation_id)
        page = await self._pages.get_page(identity, page_id)
        if page.translation_id != translation_id:
            raise BubbleNotFoundError()
        return page
