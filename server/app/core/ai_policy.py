"""Chính sách dùng LLM cho các tính năng AI do người học chủ động bấm (F05.09, F08.11, F09.01, F09.10).

Công tắc LLM và hạn mức mỗi ngày đi qua một port nhỏ. Hiện thực chạy thật là `SystemSettingsAiPolicy` (M13,
đọc cấu hình hệ thống do quản trị đặt - F13.05) được bọc bởi `VipAwareAiPolicy` (M17, hạn mức cao hơn khi đang
VIP - F17.04); `StaticAiPolicy` là giá trị cố định, dùng khi không cần đọc cấu hình (vd. test).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class AiPolicy(Protocol):
    async def llm_enabled(self) -> bool: ...

    async def daily_limit(self, user_id: int) -> int:
        """Số lượt gọi LLM tối đa mỗi ngày của người này cho tính năng này."""
        ...


class StaticAiPolicy:
    """Công tắc và hạn mức cố định."""

    def __init__(self, llm_enabled: bool, daily_limit: int) -> None:
        self._llm_enabled = llm_enabled
        self._daily_limit = daily_limit

    async def llm_enabled(self) -> bool:
        return self._llm_enabled

    async def daily_limit(self, user_id: int) -> int:
        return self._daily_limit


@dataclass(frozen=True, slots=True)
class AiPolicies:
    """Chính sách của bốn tính năng dùng LLM; lắp một lần ở `container.py` (F17.04)."""

    quiz: AiPolicy  # đề kiểm tra LLM (F09.01, F09.06)
    ai_note: AiPolicy  # Thẻ mở rộng AI (F08.11)
    grammar: AiPolicy  # phân tích ngữ pháp (F05.09)
    mistake_review: AiPolicy  # giải thích lỗi sai (F09.10)
