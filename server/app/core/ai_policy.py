"""Chính sách dùng LLM cho các tính năng AI do người học chủ động bấm (F05.09, F09.10).

Công tắc LLM và hạn mức mỗi ngày đi qua một port nhỏ. Hiện thực chạy thật là
`SystemSettingsAiPolicy` (M13, đọc cấu hình hệ thống do quản trị đặt - F13.05); `StaticAiPolicy` là giá trị
cố định, dùng khi không cần đọc cấu hình (vd. test).
"""

from __future__ import annotations

from typing import Protocol


class AiPolicy(Protocol):
    async def llm_enabled(self) -> bool: ...

    async def daily_limit(self) -> int:
        """Số lượt gọi LLM tối đa mỗi người mỗi ngày cho tính năng này."""
        ...


class StaticAiPolicy:
    """Công tắc và hạn mức cố định."""

    def __init__(self, llm_enabled: bool, daily_limit: int) -> None:
        self._llm_enabled = llm_enabled
        self._daily_limit = daily_limit

    async def llm_enabled(self) -> bool:
        return self._llm_enabled

    async def daily_limit(self) -> int:
        return self._daily_limit
