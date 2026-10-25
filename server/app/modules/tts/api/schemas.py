from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

# Chặn thô ở tầng validate; giới hạn nghiệp vụ (400/413) do domain xử lý để trả đúng mã lỗi.
TEXT_FIELD_MAX_CHARS = 10_000


class SpeakRequest(BaseModel):
    text: str = Field(max_length=TEXT_FIELD_MAX_CHARS, description="Văn bản tiếng Trung cần đọc")
    rate: Decimal | None = Field(
        default=None,
        gt=0,
        le=10,
        max_digits=6,
        decimal_places=3,
        description="Tốc độ 0,5–1,5 (ngoài khoảng được đưa về biên); bỏ trống = 1,0",
    )
    voice: str | None = Field(
        default=None, max_length=64, description="Giọng Edge TTS; bỏ trống = giọng trong cài đặt"
    )


class VoiceResponse(BaseModel):
    short_name: str = Field(
        description="Dùng làm `tts_voice` trong cài đặt hoặc tham số `voice` của POST /tts"
    )
    locale: str = Field(description="zh-CN | zh-TW | zh-HK ...")
    gender: str = Field(description="female | male")
    friendly_name: str = Field(description="Tên hiển thị tiếng Việt")


class VoiceListResponse(BaseModel):
    items: list[VoiceResponse]
    source: str = Field(description="service: lấy từ dịch vụ TTS; default: danh sách có sẵn khi dịch vụ lỗi")
