from __future__ import annotations

from collections.abc import Callable, Sequence

from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.dictionary.application.ports import DictionaryUnitOfWork
from app.modules.dictionary.domain.entities import EntryRow, ImportReport

BATCH_SIZE = 2000


class ImportDictionaryUseCase:
    """F06.06 — Nạp / cập nhật từ điển (US-QT-09). Cả lần nạp là một giao dịch; nạp lại không sinh trùng."""

    def __init__(self, uow_factory: Callable[[], DictionaryUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Identity, rows: Sequence[EntryRow]) -> ImportReport:
        if not actor.is_admin:
            raise PermissionDeniedError()
        added = updated = skipped = 0
        async with self._uow_factory() as uow:
            for start in range(0, len(rows), BATCH_SIZE):
                a, u, s = await uow.writer.upsert_entries(rows[start : start + BATCH_SIZE])
                added, updated, skipped = added + a, updated + u, skipped + s
            await uow.commit()  # gián đoạn giữa chừng thì không commit → hoàn tác toàn bộ
        return ImportReport(added=added, updated=updated, skipped=skipped)
