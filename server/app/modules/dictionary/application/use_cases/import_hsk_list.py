from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence

from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.dictionary.application.ports import DictionaryUnitOfWork
from app.modules.dictionary.domain.entities import HskRow, ImportReport
from app.modules.dictionary.domain.hsk import HSK_MAX, HSK_MIN

BATCH_SIZE = 2000


class ImportHskListUseCase:
    """F06.07 — Nạp / cập nhật danh sách HSK (US-QT-10). Dòng sai bị bỏ qua, dòng đúng vẫn được nạp.

    TODO(F06.07): sau khi có sổ tay (M07, Giai đoạn 4) tính lại cấp HSK của các từ đã lưu bằng F06.08.
    """

    def __init__(self, uow_factory: Callable[[], DictionaryUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Identity, rows: Sequence[HskRow], rejected: Sequence[str]) -> ImportReport:
        if not actor.is_admin:
            raise PermissionDeniedError()
        valid: list[HskRow] = []
        bad = list(rejected)
        for row in rows:
            if row.word and HSK_MIN <= row.level <= HSK_MAX:
                valid.append(row)
            else:
                bad.append(f"{row.word or '(trống)'}: cấp {row.level} ngoài khoảng {HSK_MIN}–{HSK_MAX}")
        added = updated = skipped = 0
        async with self._uow_factory() as uow:
            for start in range(0, len(valid), BATCH_SIZE):
                a, u, s = await uow.writer.upsert_hsk_words(valid[start : start + BATCH_SIZE])
                added, updated, skipped = added + a, updated + u, skipped + s
            await uow.commit()
        per_level = dict(sorted(Counter(row.level for row in valid).items()))
        return ImportReport(
            added=added, updated=updated, skipped=skipped, rejected=tuple(bad), per_level=per_level
        )
