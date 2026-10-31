"""Cấu hình hệ thống do quản trị viên đặt (F13.05): danh sách khóa, kiểu giá trị và khoảng hợp lệ.

Thuần Python. Giá trị lưu ở bảng `system_settings` (JSONB); khóa chưa có trong CSDL dùng mặc định
lấy từ `Settings` (xem `application/system_settings.py`).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.modules.admin.domain.errors import InvalidSettingValueError, UnknownSettingError

# Trần của mọi hạn mức mỗi ngày: chặn gõ nhầm số quá lớn làm mất tác dụng kiểm soát chi phí.
MAX_DAILY_LIMIT = 1000

MAINTENANCE_MESSAGE = "Hệ thống đang bảo trì, vui lòng quay lại sau"


class SettingKind(str, Enum):
    BOOL = "bool"
    INT = "int"
    OPTIONAL_ID = "optional_id"  # số nguyên dương hoặc null (vd. sample_page_id)


@dataclass(frozen=True, slots=True)
class SettingSpec:
    key: str
    kind: SettingKind
    label: str  # tên tiếng Việt dùng trong thông báo lỗi
    maximum: int = MAX_DAILY_LIMIT


SETTING_SPECS: dict[str, SettingSpec] = {
    spec.key: spec
    for spec in (
        SettingSpec("llm_enabled", SettingKind.BOOL, "Bật dịch vụ LLM"),
        SettingSpec("tts_enabled", SettingKind.BOOL, "Bật dịch vụ TTS"),
        SettingSpec("quiz_daily_llm_limit", SettingKind.INT, "Hạn mức đề kiểm tra LLM mỗi ngày"),
        SettingSpec("ai_note_daily_limit", SettingKind.INT, "Hạn mức Thẻ mở rộng AI mỗi ngày"),
        SettingSpec("grammar_daily_limit", SettingKind.INT, "Hạn mức phân tích ngữ pháp mỗi ngày"),
        SettingSpec("mistake_review_daily_limit", SettingKind.INT, "Hạn mức giải thích lỗi sai mỗi ngày"),
        # Hạn mức khi đang VIP (F17.04); chỉ có tác dụng nếu lớn hơn hạn mức thường tương ứng.
        SettingSpec("vip_quiz_daily_llm_limit", SettingKind.INT, "Hạn mức đề kiểm tra LLM mỗi ngày (VIP)"),
        SettingSpec("vip_ai_note_daily_limit", SettingKind.INT, "Hạn mức Thẻ mở rộng AI mỗi ngày (VIP)"),
        SettingSpec("vip_grammar_daily_limit", SettingKind.INT, "Hạn mức phân tích ngữ pháp mỗi ngày (VIP)"),
        SettingSpec(
            "vip_mistake_review_daily_limit", SettingKind.INT, "Hạn mức giải thích lỗi sai mỗi ngày (VIP)"
        ),
        SettingSpec("maintenance_mode", SettingKind.BOOL, "Chế độ bảo trì"),
        SettingSpec("auto_moderation_enabled", SettingKind.BOOL, "Kiểm duyệt ảnh tự động"),
        SettingSpec("ocr_on_upload_enabled", SettingKind.BOOL, "Xử lý OCR ngay khi tải"),
        SettingSpec("admin_notifications_enabled", SettingKind.BOOL, "Thông báo quản trị"),
        SettingSpec("sample_page_id", SettingKind.OPTIONAL_ID, "Trang mẫu", maximum=2**62),
    )
}


@dataclass(frozen=True, slots=True)
class SystemSettingsSnapshot:
    """Giá trị hiệu lực của mọi khóa (đã gộp mặc định)."""

    llm_enabled: bool
    tts_enabled: bool
    quiz_daily_llm_limit: int
    ai_note_daily_limit: int
    grammar_daily_limit: int
    mistake_review_daily_limit: int
    vip_quiz_daily_llm_limit: int
    vip_ai_note_daily_limit: int
    vip_grammar_daily_limit: int
    vip_mistake_review_daily_limit: int
    maintenance_mode: bool
    auto_moderation_enabled: bool
    ocr_on_upload_enabled: bool
    admin_notifications_enabled: bool
    sample_page_id: int | None

    def as_dict(self) -> dict[str, Any]:
        return {key: getattr(self, key) for key in SETTING_SPECS}


def validate_setting(key: str, raw: Any) -> bool | int | None:
    """Kiểm kiểu và khoảng của một giá trị; sai thì raise lỗi có thông báo cụ thể (US-QT-13 TC4)."""
    spec = SETTING_SPECS.get(key)
    if spec is None:
        raise UnknownSettingError(f"Khóa cấu hình không tồn tại: {key}")
    if spec.kind is SettingKind.BOOL:
        if not isinstance(raw, bool):
            raise InvalidSettingValueError(f"«{spec.label}» chỉ nhận giá trị bật hoặc tắt (true/false)")
        return raw
    if spec.kind is SettingKind.OPTIONAL_ID and raw is None:
        return None
    # bool là lớp con của int trong Python nên phải loại riêng.
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise InvalidSettingValueError(f"«{spec.label}» phải là số nguyên")
    minimum = 1 if spec.kind is SettingKind.OPTIONAL_ID else 0
    if raw < minimum or raw > spec.maximum:
        raise InvalidSettingValueError(
            f"«{spec.label}» phải là số nguyên từ {minimum} đến {spec.maximum}",
            details={"key": key, "minimum": minimum, "maximum": spec.maximum},
        )
    return raw
