"""Adapter tách từ (jieba) và phiên âm (pypinyin). Việc nặng CPU chạy ngoài event loop."""

from __future__ import annotations

import asyncio
import threading

import jieba
from pypinyin import Style, lazy_pinyin

_jieba_lock = threading.Lock()
_jieba_ready = False


def _ensure_jieba() -> None:
    global _jieba_ready
    with _jieba_lock:
        if not _jieba_ready:
            jieba.setLogLevel(60)  # tắt log khởi tạo
            jieba.initialize()
            _jieba_ready = True


class JiebaTokenizer:
    async def tokenize(self, text: str) -> list[str]:
        def run() -> list[str]:
            _ensure_jieba()
            return [str(word) for word in jieba.lcut(text)]

        return await asyncio.to_thread(run)


class PypinyinProvider:
    def to_pinyin(self, text: str) -> str:
        return " ".join(
            str(part).strip() for part in lazy_pinyin(text, style=Style.TONE) if str(part).strip()
        )
