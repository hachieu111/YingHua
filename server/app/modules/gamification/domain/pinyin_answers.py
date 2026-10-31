"""Đổi pinyin có dấu thành các đáp án gõ bàn phím (a-z) cho mini-game "Gõ pinyin chém chữ" (F16.01)."""

from __future__ import annotations

import re
import unicodedata
from itertools import product

_PLAIN = re.compile(r"[a-z]+")


def _syllable_forms(syllable: str) -> list[str]:
    """Dạng không dấu của một âm tiết; ü gõ là `u` (người dùng chốt). Rỗng nếu còn ký tự ngoài a-z."""
    folded = unicodedata.normalize("NFC", syllable.strip().lower()).replace("u:", "u")
    plain = "".join(ch for ch in unicodedata.normalize("NFD", folded) if not unicodedata.combining(ch))
    return [plain] if _PLAIN.fullmatch(plain) else []


def reading_answers(reading: str) -> list[str]:
    """Đáp án của một cách đọc gồm một hay nhiều âm tiết cách nhau bằng dấu cách, gõ liền không cách."""
    options = [_syllable_forms(s) for s in reading.split()]
    if not options or any(not o for o in options):
        return []
    return ["".join(parts) for parts in product(*options)]


def char_answers(pinyin: str | None) -> list[str]:
    """Đáp án của một chữ đa âm: mọi cách đọc trong `hanzi.pinyin` (cách nhau bằng dấu cách) đều đúng."""
    if not pinyin:
        return []
    found: list[str] = []
    for syllable in pinyin.split():
        found.extend(_syllable_forms(syllable))
    return list(dict.fromkeys(found))


def word_answers(pinyin: str | None) -> list[str]:
    """Đáp án của một từ: các âm tiết của `hsk_words.pinyin` gõ liền nhau."""
    if not pinyin:
        return []
    return list(dict.fromkeys(reading_answers(pinyin)))
