from __future__ import annotations

from dataclasses import dataclass

from app.modules.auth.application.public import User


@dataclass(frozen=True, slots=True)
class UserActivity:
    """Số liệu học tập và nội dung của một người dùng, do các module sở hữu dữ liệu cung cấp."""

    status_counts: dict[str, int]  # số mục từ theo trạng thái: learning, known, ignored
    total_cards: int
    due_now: int
    reviewed_today: int
    reviews_total: int
    private_series: int
    quick_uploads: int


@dataclass(frozen=True, slots=True)
class UserOverview:
    user: User
    activity: UserActivity
