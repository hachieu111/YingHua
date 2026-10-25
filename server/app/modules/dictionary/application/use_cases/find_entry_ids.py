from __future__ import annotations

from collections.abc import Callable, Collection

from app.modules.dictionary.application.ports import DictionaryUnitOfWork


class FindEntryIdsUseCase:
    """Mã mục từ điển của nhiều từ trong một truy vấn (M05/M04 gắn từ trong bong bóng với mục từ — F06.01)."""

    def __init__(self, uow_factory: Callable[[], DictionaryUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, words: Collection[str]) -> dict[str, int]:
        """Trả {từ: mã nhỏ nhất} cho các từ có mục giản thể khớp; từ không có mục thì không xuất hiện."""
        unique = sorted({w for w in words if w})
        if not unique:
            return {}
        async with self._uow_factory() as uow:
            return await uow.reader.find_entry_ids(unique)
