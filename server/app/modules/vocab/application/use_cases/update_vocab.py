from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from app.core.clock import Clock
from app.modules.admin.application.public import record_admin_action, resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.vocab.application.access import load_entry
from app.modules.vocab.application.dto import VocabDetail
from app.modules.vocab.application.ports import TermDictionary, VocabUnitOfWork
from app.modules.vocab.application.views import build_detail
from app.modules.vocab.domain.rules import apply_changes


class UpdateVocabUseCase:
    """F07.03, F07.04 — Đổi trạng thái học, ghi chú, nghĩa, dấu sao của từ (US-NH-33, US-NH-34).

    Chỉ các trường có trong `changes` được đổi. Ghi chú rỗng = xóa ghi chú; tối đa `note_max_chars` ký tự.
    "Đã thuộc"/"Bỏ qua" loại thẻ khỏi danh sách đến hạn ngay ở truy vấn của M08 nên không động tới thẻ; đưa
    về "Đang học" thì thẻ trở lại lịch ôn với trạng thái FSRS cũ.

    Quản trị viên sửa từ của người khác qua `owner_id`; việc đó ghi nhật ký `vocab.update` (F13.07, F13.06).
    """

    def __init__(
        self,
        uow_factory: Callable[[], VocabUnitOfWork],
        pages: PageAccessPort,
        dictionary: TermDictionary,
        clock: Clock,
        note_max_chars: int,
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._dictionary = dictionary
        self._clock = clock
        self._note_max_chars = note_max_chars

    async def execute(
        self, identity: Identity, entry_id: int, changes: Mapping[str, Any], owner_id: int | None = None
    ) -> VocabDetail:
        owner = resolve_owner(identity, owner_id)
        now = self._clock.now()
        async with self._uow_factory() as uow:
            entry = await load_entry(uow, owner, entry_id)
            apply_changes(entry, changes, self._note_max_chars, now)
            await uow.entries.update(entry)
            await record_admin_action(
                uow.audit,
                identity,
                owner,
                "vocab.update",
                "vocab_entry",
                entry.id,
                now,
                {"fields": sorted(changes)},
            )
            await uow.commit()
            return await build_detail(uow, self._pages, self._dictionary, identity, entry, now)
