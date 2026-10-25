"""Trích câu ví dụ Hán–Việt có sẵn trong phần giải nghĩa của từ điển Thiên Chửu.

Dạng thường gặp: `[nhất cộng] Tất cả: 一共多少 人？ Tất cả có bao nhiêu người?;`
"""

from __future__ import annotations

import re

from app.modules.dictionary.domain.pinyin import is_han_char

MAX_EXAMPLES_PER_ENTRY = 3
_MIN_HAN_CHARS = 2
_MIN_VIETNAMESE_WORDS = 2
_LATIN = re.compile(r"[A-Za-zÀ-ỹĐđ]")


def _find_han_run(part: str) -> tuple[int, int] | None:
    """Đoạn chữ Hán đầu tiên: gồm chữ Hán, dấu câu CJK, khoảng trắng và chữ số, KHÔNG có chữ Latin."""
    start = next((i for i, c in enumerate(part) if is_han_char(c)), None)
    if start is None:
        return None
    end = start
    for i in range(start, len(part)):
        c = part[i]
        if is_han_char(c):
            end = i + 1
        elif _LATIN.match(c):
            break
    return start, end


def extract_examples(gloss: str) -> list[tuple[str, str]]:
    """Trả danh sách (câu Hán, bản dịch Việt), tối đa MAX_EXAMPLES_PER_ENTRY."""
    results: list[tuple[str, str]] = []
    for part in re.split(r"[;；]", gloss):
        run = _find_han_run(part)
        if run is None:
            continue
        start, end = run
        zh = part[start:end].strip()
        # Lấy thêm dấu câu CJK đứng ngay sau chữ Hán cuối (？。！）…).
        while end < len(part) and part[end] in "？。！，、）」』”…?!.)":
            zh += part[end]
            end += 1
        vi = part[end:].strip(" :,-–—()")
        if sum(1 for c in zh if is_han_char(c)) < _MIN_HAN_CHARS:
            continue
        if len(vi.split()) < _MIN_VIETNAMESE_WORDS or not _LATIN.search(vi):
            continue
        results.append((zh, vi))
        if len(results) >= MAX_EXAMPLES_PER_ENTRY:
            break
    return results
