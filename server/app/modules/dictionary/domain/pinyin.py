"""Xử lý pinyin và nhận dạng chữ Hán — thuần Python, không phụ thuộc thư viện ngoài."""

from __future__ import annotations

import re
import unicodedata
from enum import Enum

_TONE_MARKS = {
    "a": "āáǎà",
    "e": "ēéěè",
    "i": "īíǐì",
    "o": "ōóǒò",
    "u": "ūúǔù",
    "ü": "ǖǘǚǜ",
}
_VOWELS = "aeiouü"
_SYLLABLE = re.compile(r"^([A-Za-züÜ:]+?)([1-5])?$")
_HAN_RANGES = (
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0x20000, 0x2A6DF),
)
# Chữ cái chỉ có trong pinyin có dấu (tiếng Việt không dùng).
_PINYIN_ONLY_MARKS = frozenset("āēīōūǎěǐǒǔǖǘǚǜüĀĒĪŌŪǍĚǏǑǓ")
# Chữ cái chỉ có trong tiếng Việt (pinyin không dùng).
_VIETNAMESE_ONLY = frozenset("ăâêôơưđạảãấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ")


class QueryKind(str, Enum):
    HAN = "han"
    PINYIN = "pinyin"
    VIETNAMESE = "vietnamese"
    LATIN = "latin"  # chữ Latin không dấu đặc trưng: có thể là pinyin hoặc tiếng Việt


def is_han_char(ch: str) -> bool:
    code = ord(ch)
    return any(low <= code <= high for low, high in _HAN_RANGES)


def has_han(text: str) -> bool:
    return any(is_han_char(ch) for ch in text)


def _mark_syllable(syllable: str) -> str:
    match = _SYLLABLE.match(syllable)
    if match is None:
        return syllable
    body, tone = match.group(1), match.group(2)
    body = body.replace("u:", "ü").replace("U:", "Ü")
    if tone is None or tone == "5":
        return body
    body = body.replace("v", "ü").replace("V", "Ü")  # 'v' chỉ là ü khi đi kèm số thanh (lv4 → lǜ)
    lower = body.lower()
    if "a" in lower:
        index = lower.index("a")
    elif "e" in lower:
        index = lower.index("e")
    elif "ou" in lower:
        index = lower.index("o")
    else:
        positions = [i for i, c in enumerate(lower) if c in _VOWELS]
        if not positions:
            return body
        index = positions[-1]
    mark = _TONE_MARKS[lower[index]][int(tone) - 1]
    if body[index].isupper():
        mark = mark.upper()
    return body[:index] + mark + body[index + 1 :]


def numeric_to_marks(text: str) -> str:
    """'xue2 xi2' → 'xué xí'. Âm tiết không phải pinyin (chữ cái đơn, số) được giữ nguyên."""
    return " ".join(_mark_syllable(part) for part in text.split())


def search_key(text: str) -> str:
    """Khóa so khớp pinyin: bỏ dấu thanh, số thanh, khoảng trắng; ü/v → u; chữ thường."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    stripped = stripped.replace("u:", "u").replace("U:", "u").lower().replace("v", "u")
    return re.sub(r"[\s1-5'’:]", "", stripped)


def classify_query(query: str) -> QueryKind:
    if has_han(query):
        return QueryKind.HAN
    lowered = query.lower()
    if re.fullmatch(r"[a-züv:'\s1-5]+", lowered) and re.search(r"[1-5]", lowered):
        return QueryKind.PINYIN
    if any(c in _PINYIN_ONLY_MARKS for c in query):
        return QueryKind.PINYIN
    if any(c in _VIETNAMESE_ONLY for c in lowered):
        return QueryKind.VIETNAMESE
    return QueryKind.LATIN
