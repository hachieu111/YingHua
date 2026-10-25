from __future__ import annotations

import unicodedata
from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.dictionary.application.ports import DictionaryUnitOfWork
from app.modules.dictionary.domain.entities import CharacterBreakdown
from app.modules.dictionary.domain.errors import EmptyQueryError, InvalidCharacterError, TextTooLongError
from app.modules.dictionary.domain.pinyin import is_han_char

MAX_CHARACTERS = 20


class DecomposeCharactersUseCase:
    """F06.05 — Phân rã chữ Hán: bộ thủ, thành phần, số nét; từ nhiều chữ thì xem lần lượt (US-NH-30)."""

    def __init__(self, uow_factory: Callable[[], DictionaryUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, text: str, identity: Identity | None) -> list[CharacterBreakdown]:
        text = unicodedata.normalize("NFKC", text).strip()
        if not text:
            raise EmptyQueryError()
        if len(text) > MAX_CHARACTERS:
            raise TextTooLongError(f"Tối đa {MAX_CHARACTERS} chữ mỗi lần")
        bad = next((c for c in text if not is_han_char(c)), None)
        if bad is not None:
            raise InvalidCharacterError(f"Ký tự không hợp lệ: {bad!r}. Chỉ phân rã được chữ Hán")
        chars = list(dict.fromkeys(text))
        async with self._uow_factory() as uow:
            hanzi = await uow.reader.get_hanzi(chars)
            if identity is not None:
                await uow.events.add(identity.user_id, text, None, "decompose")
                await uow.commit()
        return [CharacterBreakdown(c, hanzi.get(c)) for c in chars]
