"""Tách từ tiếng Trung (jieba) + pinyin từng từ (pypinyin) cho bong bóng.

Cùng quy tắc với `Backend/app/services/dictionary.tokenize` của bản cũ: chỉ giữ token có chữ Hán.
"""

from __future__ import annotations

import re
import threading
from typing import Any

import jieba
from pypinyin import Style, lazy_pinyin

_CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
# jieba không ghi log ở mức này (cao hơn CRITICAL) — tránh in thông báo nạp từ điển ra stdout.
_JIEBA_SILENT_LEVEL = 60
_jieba_lock = threading.Lock()
_jieba_ready = False


def _ensure_jieba() -> None:
    global _jieba_ready
    with _jieba_lock:
        if not _jieba_ready:
            jieba.setLogLevel(_JIEBA_SILENT_LEVEL)
            jieba.initialize()
            _jieba_ready = True


def has_cjk(text: str) -> bool:
    """Chuỗi có ít nhất một chữ Hán không."""
    return bool(_CJK.search(text or ""))


def pinyin_of(text: str) -> str:
    """Pinyin có dấu thanh, cách nhau bằng dấu cách (giống bản cũ)."""
    return " ".join(lazy_pinyin(text, style=Style.TONE))


def tokenize_chinese(text: str) -> list[dict[str, Any]]:
    """Trả `[{w, start, end, pinyin}]`, chỉ giữ token có chữ Hán."""
    _ensure_jieba()
    return [
        {"w": w, "start": s, "end": e, "pinyin": pinyin_of(w)}
        for w, s, e in jieba.tokenize(text)
        if has_cjk(w)
    ]
