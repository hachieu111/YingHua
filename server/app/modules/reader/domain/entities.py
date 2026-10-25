"""Thực thể của M05 Đọc truyện & Hover-Dịch — thuần Python, không phụ thuộc framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


@dataclass(frozen=True, slots=True)
class Stroke:
    """Một nét vẽ tự do: màu `#rrggbb` và danh sách điểm (x, y) theo tọa độ trang (F05.08)."""

    color: str
    points: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class AnnotationInput:
    """Ghi chú người dùng gửi lên: bong bóng tô màu và nét vẽ (F05.08)."""

    highlights: dict[int, str] = field(default_factory=dict)
    strokes: tuple[Stroke, ...] = ()


@dataclass(frozen=True, slots=True)
class Annotation:
    user_id: int
    page_id: int
    is_bookmarked: bool
    highlights: dict[int, str]
    strokes: tuple[Stroke, ...]
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class BookmarkRef:
    page_id: int
    updated_at: datetime


class ConsumeOutcome(str, Enum):
    OK = "ok"
    LIMIT_REACHED = "limit_reached"
    UNKNOWN = "unknown"  # chưa có hoặc đã hết hạn


@dataclass(frozen=True, slots=True)
class GuestQuota:
    """Hạn mức tra từ còn lại của phiên Khách (F05.04)."""

    session_id: str
    limit: int
    used: int

    @property
    def remaining(self) -> int:
        return max(self.limit - self.used, 0)
