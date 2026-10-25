"""F06.08 — Xác định cấp HSK của một từ (thuần, tra theo bảng đã nạp sẵn)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from app.modules.dictionary.domain.pinyin import is_han_char

HSK_MIN, HSK_MAX = 1, 9


class HskSource(str, Enum):
    LIST = "list"  # có trong danh sách HSK
    DERIVED = "derived"  # suy từ chữ cấu thành
    NONE = "none"  # Ngoài HSK


@dataclass(frozen=True, slots=True)
class HskInfo:
    level: int | None
    source: HskSource


NOT_IN_HSK = HskInfo(None, HskSource.NONE)


def resolve_hsk(term: str, levels: Mapping[str, int]) -> HskInfo:
    """`levels` chứa cấp của `term` và của từng chữ trong `term` nếu có trong danh sách."""
    direct = levels.get(term)
    if direct is not None:
        return HskInfo(direct, HskSource.LIST)
    chars = [c for c in term if is_han_char(c)]
    if len(chars) >= 2:
        char_levels = [levels[c] for c in chars if c in levels]
        if char_levels:
            return HskInfo(max(char_levels), HskSource.DERIVED)
    return NOT_IN_HSK
