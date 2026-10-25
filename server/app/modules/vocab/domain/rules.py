"""Quy tắc thuần của M07: chuẩn hóa từ, ghi chú, trạng thái, bộ lọc HSK, khung cắt ảnh ngữ cảnh."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.modules.vocab.domain.entities import CropBox, VocabEntry, VocabOrigin, VocabStatus
from app.modules.vocab.domain.errors import (
    InvalidHskFilterError,
    InvalidTermError,
    InvalidVocabFieldError,
    InvalidVocabSourceError,
    InvalidVocabStatusError,
    NoteTooLongError,
)

MAX_TERM_CHARS = 32
MAX_BULK_WORDS = 50  # số từ tối đa mỗi lần lưu tất cả từ của trang (F07.12)
MAX_MEANING_CHARS = 1000
HSK_MIN, HSK_MAX = 1, 9
HSK_NONE_TOKEN = "none"
SOURCE_LABEL_MAX_CHARS = 255

# Ảnh ngữ cảnh: chừa lề quanh bong bóng để thấy cả nét chữ sát mép, và giới hạn cạnh dài để ảnh nhỏ gọn.
CROP_PADDING_RATIO = 0.15
CROP_MIN_PADDING_PX = 8
SNIPPET_MAX_SIDE_PX = 640

EDITABLE_FIELDS = frozenset({"status", "note", "meaning_vi", "is_starred"})


def _is_han(ch: str) -> bool:
    code = ord(ch)
    return 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF or 0x20000 <= code <= 0x2FA1F


def normalize_term(raw: str) -> str:
    """NFKC + bỏ khoảng trắng hai đầu; phải có chữ Hán và dài tối đa `MAX_TERM_CHARS`."""
    term = unicodedata.normalize("NFKC", raw).strip()
    if not term or len(term) > MAX_TERM_CHARS or not any(_is_han(c) for c in term):
        raise InvalidTermError()
    return term


def contains_term(text: str, term: str) -> bool:
    return term in unicodedata.normalize("NFKC", text)


def clean_note(raw: str | None, max_chars: int) -> str | None:
    """Ghi chú rỗng nghĩa là xóa ghi chú (F07.04)."""
    if raw is None:
        return None
    note = raw.strip()
    if not note:
        return None
    if len(note) > max_chars:
        raise NoteTooLongError(f"Ghi chú tối đa {max_chars} ký tự")
    return note


def clean_meaning(raw: str | None) -> str | None:
    if raw is None:
        return None
    meaning = raw.strip()
    if len(meaning) > MAX_MEANING_CHARS:
        raise InvalidVocabFieldError(
            f"Nghĩa tối đa {MAX_MEANING_CHARS} ký tự", details={"field": "meaning_vi"}
        )
    return meaning or None


def parse_status(value: object) -> VocabStatus:
    try:
        return VocabStatus(value)
    except ValueError as exc:
        raise InvalidVocabStatusError() from exc


def parse_origin(value: object) -> VocabOrigin:
    try:
        return VocabOrigin(value)
    except ValueError as exc:
        raise InvalidVocabSourceError() from exc


def parse_hsk_filter(raw: str | None) -> tuple[int | None, bool]:
    """Trả (cấp HSK, ngoài HSK). `None` → không lọc; `none` → ngoài HSK; `1`..`9` → cấp đó."""
    if raw is None or raw == "":
        return None, False
    if raw.lower() == HSK_NONE_TOKEN:
        return None, True
    if raw.isdigit() and HSK_MIN <= int(raw) <= HSK_MAX:
        return int(raw), False
    raise InvalidHskFilterError()


def apply_changes(entry: VocabEntry, changes: Mapping[str, Any], note_max_chars: int, now: datetime) -> None:
    """Kiểm tra rồi áp dụng các thay đổi của người học (F07.03, F07.04, sửa nghĩa, đánh dấu sao)."""
    unknown = set(changes) - EDITABLE_FIELDS
    if unknown:
        raise InvalidVocabFieldError(details={"field": sorted(unknown)[0]})
    if "status" in changes:
        entry.status = parse_status(changes["status"])
    if "note" in changes:
        entry.note = clean_note(changes["note"], note_max_chars)
    if "meaning_vi" in changes:
        entry.meaning_vi = clean_meaning(changes["meaning_vi"])
    if "is_starred" in changes:
        flag = changes["is_starred"]
        if not isinstance(flag, bool):
            raise InvalidVocabFieldError(details={"field": "is_starred"})
        entry.is_starred = flag
    entry.updated_at = now


def snippet_box(x: int, y: int, w: int, h: int, image_w: int, image_h: int) -> CropBox | None:
    """Khung cắt quanh bong bóng (pixel ảnh gốc) có lề, kẹp trong ảnh. None nếu khung rỗng/ngoài ảnh."""
    if w <= 0 or h <= 0 or image_w <= 0 or image_h <= 0:
        return None
    pad = max(CROP_MIN_PADDING_PX, int(max(w, h) * CROP_PADDING_RATIO))
    left, top = max(0, x - pad), max(0, y - pad)
    right, bottom = min(image_w, x + w + pad), min(image_h, y + h + pad)
    if right <= left or bottom <= top:
        return None
    return CropBox(left, top, right, bottom)


def format_chapter_number(number: Decimal) -> str:
    """12 → "12", 12.5 → "12.5" (không để đuôi .0 hay ký hiệu mũ)."""
    text = format(number.normalize(), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def source_label(series_title: str | None, chapter_number: Decimal | None, page_no: int) -> str:
    """Nhãn nguồn hiển thị trên ngữ cảnh: "Truyện · Chương 3 · Trang 5" hoặc "Ảnh tải nhanh · Trang 2"."""
    if series_title is None or chapter_number is None:
        label = f"Ảnh tải nhanh · Trang {page_no}"
    else:
        label = f"{series_title} · Chương {format_chapter_number(chapter_number)} · Trang {page_no}"
    return label[:SOURCE_LABEL_MAX_CHARS]


def pinyin_of_tokens(tokens: Sequence[Any], fallback: str | None = None) -> str | None:
    """Pinyin cả câu ghép từ pinyin từng từ đã tách (F04.10); không có thì dùng pinyin nguyên bong bóng."""
    parts = [
        str(t["pinyin"]).strip()
        for t in tokens
        if isinstance(t, dict)
        and t.get("pinyin")
        and isinstance(t.get("word"), str)
        and any(_is_han(c) for c in t["word"])
    ]
    return " ".join(p for p in parts if p) or (fallback or None)


def collect_page_words(bubbles: Sequence[tuple[int, int, Sequence[Any]]]) -> list[tuple[str, int]]:
    """Từ chữ Hán khác nhau của một trang theo thứ tự đọc, kèm bong bóng ĐẦU TIÊN chứa từ (F07.12).

    `bubbles` là (mã bong bóng, thứ tự, token) của mọi bong bóng; token không phải chữ Hán (dấu câu, số,
    chữ Latinh), từ quá dài hoặc từ không nằm trong văn bản bong bóng bị bỏ.
    """
    seen: dict[str, int] = {}
    for bubble_id, _, tokens in sorted(bubbles, key=lambda b: b[1]):
        for token in tokens:
            word = token.get("word") if isinstance(token, dict) else None
            if not isinstance(word, str) or word in seen or not 0 < len(word) <= MAX_TERM_CHARS:
                continue
            if all(_is_han(c) for c in word):
                seen[word] = bubble_id
    return list(seen.items())
