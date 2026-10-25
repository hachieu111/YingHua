from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.storage import FileStorage, StagedFiles
from app.modules.admin.application.public import record_admin_action, resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.vocab.application.access import load_entry
from app.modules.vocab.application.ports import VocabUnitOfWork


class DeleteVocabUseCase:
    """F07.06 — Xóa từ khỏi sổ tay cùng toàn bộ dữ liệu đi kèm (US-NH-36).

    Một giao dịch xóa mục từ; ngữ cảnh, thẻ và lượt ôn đi theo nhờ `ON DELETE CASCADE`, ảnh cắt bị xóa khỏi
    bảng tệp và (sau commit) khỏi kho. Lưu lại từ này sau đó được xem như từ mới, lịch ôn bắt đầu lại.
    Quản trị viên xóa từ của người khác qua `owner_id`; việc đó ghi nhật ký `vocab.delete` (F13.07).
    """

    def __init__(
        self, uow_factory: Callable[[], VocabUnitOfWork], storage: FileStorage, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._storage = storage
        self._clock = clock

    async def execute(self, identity: Identity, entry_id: int, owner_id: int | None = None) -> None:
        owner = resolve_owner(identity, owner_id)
        staged = StagedFiles(self._storage)
        async with self._uow_factory() as uow:
            entry = await load_entry(uow, owner, entry_id)
            file_ids = await uow.contexts.snippet_file_ids(entry.id)
            await uow.entries.delete(owner, entry.id)
            await record_admin_action(
                uow.audit,
                identity,
                owner,
                "vocab.delete",
                "vocab_entry",
                entry.id,
                self._clock.now(),
                {"term": entry.term},
            )
            staged.delete_after_commit(await uow.files.delete_many(file_ids))
            await uow.commit()
        await staged.finalize()
