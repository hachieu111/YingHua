from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.admin.application.public import record_admin_action, resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.vocab.application.ports import VocabUnitOfWork
from app.modules.vocab.domain.errors import SavedSentenceNotFoundError


class DeleteSavedSentenceUseCase:
    """F07.11 — Bỏ lưu một câu thoại (US-NH-70). Không ảnh hưởng sổ tay từ, thẻ ôn hay trang đang đọc.

    Quản trị viên xóa câu của người khác qua `owner_id`; việc đó ghi nhật ký `saved_sentence.delete` (F13.07).
    """

    def __init__(self, uow_factory: Callable[[], VocabUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, sentence_id: int, owner_id: int | None = None) -> None:
        owner = resolve_owner(identity, owner_id)
        async with self._uow_factory() as uow:
            sentence = await uow.sentences.get(owner, sentence_id)
            if sentence is None:
                raise SavedSentenceNotFoundError()
            await uow.sentences.delete(owner, sentence.id)
            await record_admin_action(
                uow.audit,
                identity,
                owner,
                "saved_sentence.delete",
                "saved_sentence",
                sentence.id,
                self._clock.now(),
                {"bubble_id": sentence.bubble_id},
            )
            await uow.commit()
