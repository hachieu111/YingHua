from __future__ import annotations

from app.modules.dictionary.application.ports import PinyinProvider, Tokenizer
from app.modules.dictionary.domain.entities import Token
from app.modules.dictionary.domain.errors import EmptyQueryError, TextTooLongError
from app.modules.dictionary.domain.pinyin import has_han

MAX_TEXT_LENGTH = 1000


class SegmentSentenceUseCase:
    """F06.04 — Tách câu thành từ kèm pinyin (US-NH-29). Số, dấu câu, chữ Latin giữ nguyên và không tra."""

    def __init__(self, tokenizer: Tokenizer, pinyin: PinyinProvider) -> None:
        self._tokenizer = tokenizer
        self._pinyin = pinyin

    async def execute(self, text: str) -> list[Token]:
        text = text.strip()
        if not text:
            raise EmptyQueryError("Vui lòng nhập nội dung cần tách từ")
        if len(text) > MAX_TEXT_LENGTH:
            raise TextTooLongError(f"Nội dung tối đa {MAX_TEXT_LENGTH} ký tự")
        tokens: list[Token] = []
        for word in await self._tokenizer.tokenize(text):
            if not word.strip():
                continue
            lookupable = has_han(word)
            tokens.append(Token(word, self._pinyin.to_pinyin(word) if lookupable else None, lookupable))
        return tokens
