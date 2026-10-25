from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.storage import FileStorage, StagedFiles
from app.modules.admin.application.public import record_admin_action, resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.vocab.application.access import load_entry
from app.modules.vocab.application.ports import VocabUnitOfWork
from app.modules.vocab.domain.errors import VocabContextNotFoundError


class DeleteContextUseCase:
    """F07.05 — Xóa một ngữ cảnh của từ (US-NH-35). Từ và thẻ giữ nguyên, kể cả khi xóa ngữ cảnh cuối cùng.

    Ảnh cắt của ngữ cảnh bị xóa cùng (tệp thật chỉ xóa sau khi giao dịch commit). Quản trị viên xóa của người
    khác qua `owner_id`; việc đó ghi nhật ký `vocab.context_delete` (F13.07).
    """

    def __init__(
        self, uow_factory: Callable[[], VocabUnitOfWork], storage: FileStorage, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._storage = storage
        self._clock = clock

    async def execute(
        self, identity: Identity, entry_id: int, context_id: int, owner_id: int | None = None
    ) -> None:
        owner = resolve_owner(identity, owner_id)
        staged = StagedFiles(self._storage)
        async with self._uow_factory() as uow:
            entry = await load_entry(uow, owner, entry_id)
            context = await uow.contexts.get(entry.id, context_id)
            if context is None:
                raise VocabContextNotFoundError()
            await uow.contexts.delete(context.id)
            await record_admin_action(
                uow.audit,
                identity,
                owner,
                "vocab.context_delete",
                "vocab_context",
                context.id,
                self._clock.now(),
                {"vocab_entry_id": entry.id},
            )
            if context.snippet_file_id is not None:
                staged.delete_after_commit(await uow.files.delete_many([context.snippet_file_id]))
            await uow.commit()
        await staged.finalize()
