from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any, Protocol

from app.modules.dictionary.domain.entities import (
    DictEntry,
    EntryRow,
    Example,
    HanziInfo,
    HskRow,
    SearchHit,
    SharedComponent,
    SpecializedMeaning,
    TatoebaExample,
    TermSample,
    WordOfTheDay,
)
from app.modules.dictionary.domain.pinyin import QueryKind


class DictionaryReader(Protocol):
    async def find_entries(self, term: str) -> list[DictEntry]:
        """Các mục có chữ giản thể hoặc phồn thể đúng bằng `term` (mọi nguồn, mọi cách đọc)."""
        ...

    async def find_entry_ids(self, words: Sequence[str]) -> dict[str, int]:
        """Mã nhỏ nhất của các mục có chữ giản thể đúng bằng từng từ; từ không có mục thì vắng mặt."""
        ...

    async def get_hanzi(self, chars: Sequence[str]) -> dict[str, HanziInfo]: ...

    async def get_hsk_levels(self, words: Sequence[str]) -> dict[str, int]: ...

    async def get_examples(self, entry_ids: Sequence[int]) -> dict[int, list[Example]]: ...

    async def get_specialized(self, term: str) -> list[SpecializedMeaning]:
        """Mục từ điển tu tiên (tên riêng / cụm từ) của `term`."""
        ...

    async def search(
        self, query: str, kind: QueryKind, offset: int, limit: int
    ) -> tuple[list[SearchHit], int]: ...

    async def word_of_the_day(self, level: int, day: date) -> WordOfTheDay | None: ...

    async def sample_hsk_words(self, level: int, limit: int, exclude: Sequence[str]) -> list[TermSample]:
        """Tối đa `limit` từ HSK ngẫu nhiên của cấp `level` có nghĩa Việt, bỏ các từ trong `exclude`."""
        ...

    async def find_tatoeba_examples(self, term: str, max_difficulty: int, limit: int) -> list[TatoebaExample]:
        """Câu Tatoeba của từ có độ khó đã tính và ≤ `max_difficulty` (F09.09)."""
        ...

    async def get_tatoeba_examples(self, example_ids: Sequence[int]) -> dict[int, TatoebaExample]: ...

    async def sample_translations(self, difficulty: int, exclude_ids: Sequence[int], limit: int) -> list[str]:
        """Bản dịch Việt ngẫu nhiên của các câu Tatoeba khác cùng độ khó."""
        ...

    async def terms_with_examples(self, terms: Sequence[str], max_difficulty: int) -> set[str]:
        """Tập con của `terms` có ít nhất một câu Tatoeba đạt độ khó."""
        ...

    async def hsk_words_containing(
        self, chars: Sequence[str], max_level: int, limit: int
    ) -> list[tuple[str, int]]:
        """Từ HSK (từ, cấp) có chứa ít nhất một trong `chars`, cấp ≤ `max_level`."""
        ...

    async def chars_sharing_components(self, chars: Sequence[str], limit: int) -> list[SharedComponent]:
        """Chữ khác có chung bộ thủ/thành phần với một trong `chars` (bảng hanzi)."""
        ...

    async def find_compounds(self, term: str, limit: int) -> list[DictEntry]:
        """Từ ghép/cụm ngắn (≤ 6 chữ) chứa `term`, có nghĩa Việt, phổ biến trước (F08.11)."""
        ...

    async def brief_entries(self, terms: Sequence[str]) -> dict[str, DictEntry]:
        """Mỗi từ một mục tiêu biểu (ưu tiên CVDICT vì nghĩa ngắn gọn); từ không có mục thì vắng mặt."""
        ...


class DictionaryWriter(Protocol):
    async def upsert_entries(self, rows: Sequence[EntryRow]) -> tuple[int, int, int]:
        """Trả (thêm mới, cập nhật, bỏ qua vì không đổi)."""
        ...

    async def upsert_hsk_words(self, rows: Sequence[HskRow]) -> tuple[int, int, int]: ...


class LookupEventRepository(Protocol):
    async def add(self, user_id: int, term: str, entry_id: int | None, action: str) -> None: ...

    async def recent_terms(self, user_id: int, limit: int) -> list[str]:
        """Các từ người dùng đã tra gần đây nhất (hover/tra cứu), không trùng, mới nhất trước."""
        ...

    async def count_by_term(self, user_id: int, terms: Sequence[str]) -> dict[str, int]:
        """Số lần người dùng đã tra (hover/tra cứu) từng từ; từ chưa tra thì vắng mặt (F10.01)."""
        ...


class Tokenizer(Protocol):
    async def tokenize(self, text: str) -> list[str]: ...


class PinyinProvider(Protocol):
    def to_pinyin(self, text: str) -> str:
        """Pinyin có dấu thanh, cách nhau bằng khoảng trắng."""
        ...


class DictionaryUnitOfWork(Protocol):
    @property
    def reader(self) -> DictionaryReader: ...

    @property
    def writer(self) -> DictionaryWriter: ...

    @property
    def events(self) -> LookupEventRepository: ...

    async def __aenter__(self) -> DictionaryUnitOfWork: ...

    async def __aexit__(self, *exc_info: Any) -> None: ...

    async def commit(self) -> None: ...


Settings = Mapping[str, object]
