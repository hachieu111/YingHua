"""Nguồn dữ liệu của F12.04 "Hôm nay nên học gì"; module sở hữu dữ liệu hiện thực qua `public`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.modules.auth.application.public import Identity


@dataclass(frozen=True, slots=True)
class WeakWords:
    """Số từ đủ điều kiện ra đề (F09.01) và số từ trong đó có độ nhớ R thấp (F08.02)."""

    eligible: int
    low: int


class WeakWordsSource(Protocol):
    async def weak_words(self, user_id: int, threshold: float, now: datetime) -> WeakWords: ...


class WeeklyGoalSource(Protocol):
    async def weekly_page_goal(self, identity: Identity, owner_id: int) -> int | None:
        """Mục tiêu số trang đọc mỗi tuần (M02); None nếu chưa đặt."""
        ...


class ChapterSuggestionSource(Protocol):
    async def top_terms(self, identity: Identity, owner_id: int, chapter_id: int, limit: int) -> list[str]:
        """Vài từ gợi ý đứng đầu của chương (F10.01), tính cho `owner_id`."""
        ...
