"""Tra mã mục từ theo lô (F06.01) bằng fake, không cần CSDL."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.modules.dictionary.application.public import FindEntryIdsUseCase


class FakeReader:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def find_entry_ids(self, words: Sequence[str]) -> dict[str, int]:
        self.calls.append(list(words))
        table = {"你好": 3, "吗": 9}
        return {w: table[w] for w in words if w in table}


class FakeUow:
    def __init__(self, reader: FakeReader) -> None:
        self.reader = reader

    async def __aenter__(self) -> FakeUow:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None


async def test_find_entry_ids_queries_once_with_unique_words() -> None:
    reader = FakeReader()
    use_case = FindEntryIdsUseCase(lambda: FakeUow(reader))  # type: ignore[arg-type, return-value]

    result = await use_case.execute(["吗", "你好", "吗", "", "无此词"])

    assert result == {"你好": 3, "吗": 9}
    assert reader.calls == [["你好", "吗", "无此词"]]


async def test_find_entry_ids_empty_input_skips_database() -> None:
    reader = FakeReader()
    use_case = FindEntryIdsUseCase(lambda: FakeUow(reader))  # type: ignore[arg-type, return-value]

    assert await use_case.execute([""]) == {}
    assert reader.calls == []
