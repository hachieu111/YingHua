from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.vocab.application.dto import SavedSentenceItem
from app.modules.vocab.application.ports import VocabUnitOfWork
from app.modules.vocab.application.sentence_views import build_sentence_items
from app.modules.vocab.domain.errors import SavedSentenceNotFoundError
from app.modules.vocab.domain.rules import clean_note


class UpdateSavedSentenceUseCase:
    """F07.11 — Sửa ghi chú của câu thoại đã lưu; ghi chú rỗng nghĩa là xóa ghi chú (US-NH-70)."""

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

    async def execute(self, identity: Identity, sentence_id: int, note: str | None) -> SavedSentenceItem:
        cleaned = clean_note(note, self._note_max_chars)
        async with self._uow_factory() as uow:
            sentence = await uow.sentences.get(identity.user_id, sentence_id)
            if sentence is None:
                raise SavedSentenceNotFoundError()
            now = self._clock.now()
            await uow.sentences.update_note(identity.user_id, sentence.id, cleaned, now)
            await uow.commit()
            sentence.note, sentence.updated_at = cleaned, now
            return (await build_sentence_items(uow, self._pages, identity, [sentence]))[0]
