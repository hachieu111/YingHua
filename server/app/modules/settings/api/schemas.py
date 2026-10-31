from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, StrictBool

from app.modules.settings.domain.entities import UserSettings

# Trùng với TOUR_KEYS ở domain; Pydantic cần danh sách cố định để từ chối khóa lạ bằng 422.
TourKey = Literal[
    "home",
    "reader",
    "upload",
    "library",
    "flashcards",
    "leaderboard",
    "profile",
    "shop",
    "game",
    "sample",
    "admin",
]


class SettingsResponse(BaseModel):
    hsk_level: int | None
    default_mode: Literal["read", "learn"]
    tts_voice: str | None
    learning_goal: Literal["study", "entertainment", "both"] | None
    weekly_page_goal: int | None
    show_xianxia: bool
    bubble_font_scale: int = Field(description="Cỡ chữ lớp dịch trên trang, %: 80..160, bước 10 (F02.04)")
    reminder_enabled: bool = Field(description="Bật nhắc ôn hằng ngày (F14.03)")
    reminder_time: str | None = Field(description='Giờ nhắc "HH:MM" theo múi giờ của người học (F14.03)')
    timezone: str = Field(description='Múi giờ của người học, dùng cho "hôm nay", chuỗi ngày và giờ nhắc')
    show_on_leaderboard: bool = Field(description="Hiện tên trên bảng xếp hạng; tắt thì ẩn danh (F16.08)")
    dismissed_tours: list[str] = Field(description='Hướng dẫn người mới đã chọn "không nhắc lại" (F02.05)')

    @classmethod
    def from_entity(cls, s: UserSettings) -> SettingsResponse:
        return cls(
            hsk_level=s.hsk_level,
            default_mode=s.default_mode.value,
            tts_voice=s.tts_voice,
            learning_goal=s.learning_goal.value if s.learning_goal else None,
            weekly_page_goal=s.weekly_page_goal,
            show_xianxia=s.show_xianxia,
            bubble_font_scale=s.bubble_font_scale,
            reminder_enabled=s.reminder_enabled,
            reminder_time=s.reminder_time.strftime("%H:%M") if s.reminder_time else None,
            timezone=s.timezone,
            show_on_leaderboard=s.show_on_leaderboard,
            dismissed_tours=list(s.dismissed_tours),
        )


class UpdateSettingsRequest(BaseModel):
    """Chỉ trường có trong yêu cầu được đổi; `hsk_level: null` đưa về "Chưa chọn"."""

    # Kiểm tra giá trị chi tiết ở domain để thông báo lỗi tiếng Việt thống nhất.
    hsk_level: int | None = None
    default_mode: str | None = Field(default=None, max_length=8)
    tts_voice: str | None = Field(default=None, max_length=64)
    learning_goal: str | None = Field(default=None, max_length=16)
    weekly_page_goal: int | None = None
    show_xianxia: bool | None = None
    bubble_font_scale: int | None = Field(default=None, description="80..160, bội số của 10 (F02.04)")
    reminder_enabled: bool | None = Field(default=None, description="Bật/tắt nhắc ôn (F14.03)")
    reminder_time: str | None = Field(default=None, max_length=5, description='"HH:MM"; null để xóa giờ nhắc')
    show_on_leaderboard: StrictBool | None = Field(
        default=None, description="Hiện/ẩn danh trên bảng xếp hạng (F16.08); phải là boolean"
    )
    dismissed_tours: list[TourKey] | None = Field(
        default=None,
        max_length=16,
        description='Thay toàn bộ danh sách hướng dẫn "không nhắc lại" (F02.05); [] để xem lại hướng dẫn',
    )
