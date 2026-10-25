"""Rút gọn nghĩa từ điển thành một cụm ngắn để làm đáp án/gợi ý (dùng chung M09 Kiểm tra và M10 Gợi ý)."""

from __future__ import annotations

import re
from collections.abc import Iterable

SHORT_MEANING_MAX_CHARS = 80

_HAN = "一-鿿㐀-䶿"
_DASH_RUN = re.compile(r"-{5,}")  # dải gạch ngăn phần ví dụ/chú giải dài khỏi nghĩa chính
_LEADING_BRACKET = re.compile(r"^\s*\[[^\]]*\]\s*")  # "[ái] Như 愛": phần đọc Hán Việt không phải nghĩa
# CVDICT ghi tham chiếu dạng "一塊|一块[yi1 kuai4]": giữ chữ giản thể, bỏ phồn thể và pinyin số.
_HAN_REFERENCE = re.compile(rf"(?:[{_HAN}]+\|)?([{_HAN}]+)\s*\[[^\]]*\]")
_NUMERIC_PINYIN = re.compile(r"\s*\[[A-Za-zü:\s]*\d[A-Za-zü:\d\s]*\]")  # "[ba3]" đứng riêng
_EMPTY_PARENS = re.compile(r"\(\s*\)")
_SPACE_INSIDE_PARENS = re.compile(r"\(\s+|\s+\)")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([;,.:])")
# Nghĩa chỉ là tham chiếu sang mục khác ("biến thể của X", "xem X", "như X"), chưa phải nghĩa thật.
_REFERENCE = re.compile(rf"^(?:biến thể\b.*?\bcủa|xem|như)\s+[{_HAN}]", re.IGNORECASE)
_SENSE_MARKER = "①"
_NEXT_SENSE_MARKER = "②"
_TRAILING_PUNCTUATION = " \t\r\n;,.:-"


def _clean_markup(text: str) -> str:
    text = _HAN_REFERENCE.sub(r"\1", text)
    text = _NUMERIC_PINYIN.sub("", text)
    text = _EMPTY_PARENS.sub("", text)
    text = _SPACE_INSIDE_PARENS.sub(lambda m: "(" if m.group().startswith("(") else ")", text)
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)
    return " ".join(text.split())


def is_reference_meaning(text: str | None) -> bool:
    """Nghĩa chỉ là "biến thể của …"/"xem …"/"như …" trỏ sang mục khác."""
    return bool(text) and _REFERENCE.match(short_meaning(text, max_chars=10_000)) is not None


def best_gloss(glosses: Iterable[str | None]) -> str:
    """Nghĩa đầu tiên không phải tham chiếu; chỉ toàn tham chiếu thì lấy nghĩa đầu tiên có nội dung."""
    first_usable = ""
    for gloss in glosses:
        if not short_meaning(gloss):
            continue
        if not is_reference_meaning(gloss):
            return gloss or ""
        first_usable = first_usable or (gloss or "")
    return first_usable


def short_meaning(text: str | None, max_chars: int = SHORT_MEANING_MAX_CHARS) -> str:
    """Nghĩa ngắn của một chuỗi nghĩa từ điển; chuỗi rỗng nếu không còn gì dùng được.

    Bỏ phần sau dải ≥5 dấu gạch, bỏ "[...]" ở đầu và ký hiệu CVDICT (`繁|简[pinyin số]`, `[pinyin số]`),
    chỉ lấy nghĩa ① (cắt trước "②"). Nếu có nhiều nghĩa cách nhau ";" thì bỏ nghĩa chỉ-tham-chiếu khi còn
    nghĩa khác. Cuối cùng cắt không quá `max_chars` ký tự ở ranh giới từ để không xé đôi một từ.
    """
    if not text:
        return ""
    result = _DASH_RUN.split(text, maxsplit=1)[0]
    result = _LEADING_BRACKET.sub("", result)
    result = result.split(_NEXT_SENSE_MARKER, maxsplit=1)[0]
    result = _clean_markup(result.replace(_SENSE_MARKER, " "))
    parts = [p.strip() for p in result.split(";") if p.strip()]
    useful = [p for p in parts if not _REFERENCE.match(p)]
    result = "; ".join(useful or parts)
    if len(result) > max_chars:
        window = result[: max_chars + 1]  # lấy dư một ký tự để biết ký tự sau giới hạn có phải khoảng trắng
        boundary = window.rfind(" ")
        # Chuỗi không có khoảng trắng (vd. toàn chữ Hán) thì cắt cứng tại giới hạn.
        result = window[:boundary] if boundary > 0 else window[:max_chars]
    return result.strip(_TRAILING_PUNCTUATION)
