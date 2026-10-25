from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.modules.settings.domain.entities import UserSettings


class SettingsResponse(BaseModel):
    hsk_level: int | None
    default_mode: Literal["read", "learn"]
    tts_voice: str | None
    learning_goal: Literal["study", "entertainment", "both"] | None
    weekly_page_goal: int | None
    show_xianxia: bool
    bubble_font_scale: int = Field(description="Cỡ chữ lớp dịch trên trang, %: 80..160, bước 10 (F02.04)")

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
