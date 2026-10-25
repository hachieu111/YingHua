from __future__ import annotations

from typing import Any

from app.modules.dictionary.domain.entities import EtymologyInfo, StrokeData

MAX_STROKES = 64


def _point(raw: Any) -> tuple[int, int] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        return None
    x, y = raw
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in (x, y)):
        return None
    return int(x), int(y)


def parse_stroke_data(raw: Any) -> StrokeData | None:
    """Kiểm cấu trúc dữ liệu nét; hỏng hoặc thiếu thì trả None để API vẫn dùng được (F06.05)."""
    if not isinstance(raw, dict):
        return None
    strokes, medians = raw.get("strokes"), raw.get("medians")
    if not isinstance(strokes, list) or not isinstance(medians, list):
        return None
    if not strokes or len(strokes) != len(medians) or len(strokes) > MAX_STROKES:
        return None
    if not all(isinstance(s, str) and s for s in strokes):
        return None
    parsed: list[tuple[tuple[int, int], ...]] = []
    for median in medians:
        if not isinstance(median, list) or not median:
            return None
        points = [_point(p) for p in median]
        if any(p is None for p in points):
            return None
        parsed.append(tuple(p for p in points if p is not None))
    return StrokeData(strokes=tuple(strokes), medians=tuple(parsed))


def parse_etymology(raw: Any) -> EtymologyInfo | None:
    """Chỉ giữ các trường chuỗi; không có trường nào dùng được thì trả None."""
    if not isinstance(raw, dict):
        return None

    def text_of(key: str) -> str | None:
        value = raw.get(key)
        return value if isinstance(value, str) and value else None

    info = EtymologyInfo(
        type=text_of("type"),
        hint=text_of("hint"),
        phonetic=text_of("phonetic"),
        semantic=text_of("semantic"),
    )
    return info if any((info.type, info.hint, info.phonetic, info.semantic)) else None
