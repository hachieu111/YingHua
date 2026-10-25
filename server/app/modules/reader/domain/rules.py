"""Quy tắc thuần của M05: kiểm ghi chú trên trang, bản sửa dịch, tỷ lệ phần trăm tọa độ."""

from __future__ import annotations

import json
import math
import re
import unicodedata

from app.modules.reader.domain.entities import AnnotationInput
from app.modules.reader.domain.errors import (
    AnnotationTooLargeError,
    EditTooLongError,
    EmptyTranslationError,
    InvalidAnnotationError,
)

MAX_EDIT_CHARS = 1000
MAX_STROKES = 500
MAX_TOTAL_STROKE_POINTS = 50_000
MAX_HIGHLIGHTS = 500
MAX_ANNOTATION_BYTES = 256 * 1024
MAX_COORDINATE = 1_000_000.0
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def clean_edit_text(text: str) -> str:
    """Bản sửa dịch hợp lệ: không rỗng sau khi cắt khoảng trắng, tối đa `MAX_EDIT_CHARS` ký tự (F05.05)."""
    cleaned = text.strip()
    if not cleaned:
        raise EmptyTranslationError()
    if len(cleaned) > MAX_EDIT_CHARS:
        raise EditTooLongError(f"Bản dịch tối đa {MAX_EDIT_CHARS} ký tự")
    return cleaned


def validate_annotations(data: AnnotationInput) -> None:
    """Raise InvalidAnnotationError / AnnotationTooLargeError nếu ghi chú vi phạm giới hạn (F05.08)."""
    if len(data.highlights) > MAX_HIGHLIGHTS:
        raise AnnotationTooLargeError(f"Tối đa {MAX_HIGHLIGHTS} bong bóng được tô màu")
    if len(data.strokes) > MAX_STROKES:
        raise AnnotationTooLargeError(f"Tối đa {MAX_STROKES} nét vẽ trên một trang")
    for color in data.highlights.values():
        if not _HEX_COLOR.match(color):
            raise InvalidAnnotationError("Màu phải có dạng #rrggbb")
    total_points = 0
    for stroke in data.strokes:
        if not _HEX_COLOR.match(stroke.color):
            raise InvalidAnnotationError("Màu phải có dạng #rrggbb")
        if not stroke.points:
            raise InvalidAnnotationError("Nét vẽ phải có ít nhất một điểm")
        total_points += len(stroke.points)
        if total_points > MAX_TOTAL_STROKE_POINTS:
            raise AnnotationTooLargeError(f"Tổng số điểm vẽ tối đa {MAX_TOTAL_STROKE_POINTS}")
        for x, y in stroke.points:
            if (
                not (math.isfinite(x) and math.isfinite(y))
                or abs(x) > MAX_COORDINATE
                or abs(y) > MAX_COORDINATE
            ):
                raise InvalidAnnotationError("Tọa độ nét vẽ không hợp lệ")
    if serialized_size(data) > MAX_ANNOTATION_BYTES:
        raise AnnotationTooLargeError(f"Ghi chú tối đa {MAX_ANNOTATION_BYTES // 1024} KB")


def serialized_size(data: AnnotationInput) -> int:
    """Kích thước (byte) của ghi chú khi lưu dạng JSON gọn."""
    payload = {
        "highlights": {str(k): v for k, v in data.highlights.items()},
        "strokes": [
            {"color": s.color, "points": [{"x": x, "y": y} for x, y in s.points]} for s in data.strokes
        ],
    }
    return len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))


def percent(value: int, total: int | None) -> float | None:
    """Tỷ lệ phần trăm (4 chữ số thập phân) của `value` trên `total`; None khi chưa biết kích thước ảnh."""
    if not total:
        return None
    return round(value * 100 / total, 4)


def contains_word(text_zh: str, word: str) -> bool:
    """Từ cần tra có nằm trong văn bản bong bóng (so sánh sau chuẩn hóa NFKC, bỏ khoảng trắng đầu/cuối)."""
    needle = unicodedata.normalize("NFKC", word).strip()
    return bool(needle) and needle in unicodedata.normalize("NFKC", text_zh)
