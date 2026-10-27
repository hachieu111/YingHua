"""Luật kiểm duyệt ảnh tự động đơn giản (F13.05 mở rộng, F13.04): không dùng mô hình AI nhận dạng nội dung."""

from __future__ import annotations

from enum import Enum

from app.modules.admin.domain.errors import RemovalReasonRequiredError

# Cạnh ngắn dưới mức này khó là một trang truyện đọc được (ảnh icon, ảnh rác).
MIN_PAGE_SIDE_PX = 200
# Cạnh dài hơn mức này bất thường (ảnh ghép khổng lồ, nghi tấn công tài nguyên).
MAX_PAGE_SIDE_PX = 12000
MAX_REMOVAL_REASON_LENGTH = 500


class ModerationFlag(str, Enum):
    TINY_IMAGE = "tiny_image"
    OVERSIZED_IMAGE = "oversized_image"
    DUPLICATE_IMAGE = "duplicate_image"  # cùng nội dung với ảnh khác đang còn hiển thị
    PROCESSING_FAILED = "processing_failed"  # xử lý OCR/dịch lỗi: tỉ lệ OCR lỗi cao là dấu hiệu ảnh lạ


def moderation_flags(
    width: int | None, height: int | None, duplicates: int, processing_failed: bool
) -> list[ModerationFlag]:
    """Cờ nghi vấn của một ảnh tải lên, theo thứ tự cố định."""
    flags: list[ModerationFlag] = []
    if width and height:
        if min(width, height) < MIN_PAGE_SIDE_PX:
            flags.append(ModerationFlag.TINY_IMAGE)
        if max(width, height) > MAX_PAGE_SIDE_PX:
            flags.append(ModerationFlag.OVERSIZED_IMAGE)
    if duplicates > 0:
        flags.append(ModerationFlag.DUPLICATE_IMAGE)
    if processing_failed:
        flags.append(ModerationFlag.PROCESSING_FAILED)
    return flags


def clean_removal_reason(reason: str | None) -> str:
    """Lý do gỡ là bắt buộc (F13.04); cắt theo độ dài cột."""
    cleaned = (reason or "").strip()
    if not cleaned:
        raise RemovalReasonRequiredError()
    return cleaned[:MAX_REMOVAL_REASON_LENGTH]
