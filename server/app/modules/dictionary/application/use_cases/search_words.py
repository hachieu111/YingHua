from __future__ import annotations

import unicodedata
from collections.abc import Callable

from app.modules.dictionary.application.ports import DictionaryUnitOfWork
from app.modules.dictionary.domain.entities import SearchPage
from app.modules.dictionary.domain.errors import EmptyQueryError, TextTooLongError
from app.modules.dictionary.domain.pinyin import classify_query

MAX_QUERY_LENGTH = 64
MAX_PAGE_SIZE = 50


class SearchWordsUseCase:
    """F06.02 — Tìm từ bằng chữ Hán, pinyin (có/không dấu) hoặc nghĩa tiếng Việt (US-NH-27)."""

    def __init__(self, uow_factory: Callable[[], DictionaryUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, query: str, page: int = 1, size: int = 20) -> SearchPage:
        query = unicodedata.normalize("NFKC", query).strip()
        if not query:
            raise EmptyQueryError()
        if len(query) > MAX_QUERY_LENGTH:
            raise TextTooLongError(f"Từ khóa tối đa {MAX_QUERY_LENGTH} ký tự")
        size = max(1, min(size, MAX_PAGE_SIZE))
        page = max(1, page)
        async with self._uow_factory() as uow:
            hits, total = await uow.reader.search(query, classify_query(query), (page - 1) * size, size)
        return SearchPage(items=hits, total=total, page=page, size=size)
