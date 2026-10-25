"""Độ khó của câu ví dụ (F09.09): cấp HSK cao nhất của các từ chữ Hán trong câu (thuần, tra theo bảng)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from app.modules.dictionary.domain.pinyin import is_han_char

UNKNOWN_WORD_LEVEL = 7  # từ và các chữ cấu thành đều ngoài danh sách HSK: coi như nhóm cao nhất (7-9)


def token_level(token: str, levels: Mapping[str, int]) -> int:
    """Cấp một từ: theo danh sách, không có thì lấy cấp cao nhất của chữ cấu thành, không nữa thì 7."""
    direct = levels.get(token)
    if direct is not None:
        return direct
    char_levels = [levels[c] for c in token if c in levels]
    return max(char_levels) if char_levels else UNKNOWN_WORD_LEVEL


def example_difficulty(tokens: Iterable[str], levels: Mapping[str, int]) -> int | None:
    """Cấp HSK cao nhất của các token chữ Hán; None nếu câu không có token chữ Hán nào."""
    han_tokens = [t for t in tokens if t and all(is_han_char(c) for c in t)]
    if not han_tokens:
        return None
    return max(token_level(t, levels) for t in han_tokens)
