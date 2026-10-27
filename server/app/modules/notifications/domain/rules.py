"""Quy tắc thuần của M14: kiểm tra báo lỗi, tới giờ nhắc chưa, nội dung lời nhắc."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.modules.notifications.domain.entities import ReportStatus, ReportType
from app.modules.notifications.domain.errors import (
    InvalidReportStatusError,
    InvalidReportTypeError,
    ReportContentRequiredError,
    ReportTextTooLongError,
)

MAX_DESCRIPTION_CHARS = 1000
MAX_NOTE_CHARS = 1000
MAX_TITLE_CHARS = 200


def parse_report_type(value: str | None) -> ReportType | None:
    """None/rỗng nghĩa là người học chưa chọn loại lỗi."""
    if value is None or value == "":
        return None
    try:
        return ReportType(value)
    except ValueError as exc:
        raise InvalidReportTypeError() from exc


def normalize_report(report_type: str | None, description: str | None) -> tuple[ReportType, str]:
    """F14.01 — Phải chọn ít nhất một loại lỗi hoặc có mô tả. Loại "khác" không đủ nếu thiếu mô tả.

    Có mô tả mà chưa chọn loại thì tính là "khác". Mô tả thừa khoảng trắng được cắt, tối đa 1000 ký tự.
    """
    parsed = parse_report_type(report_type)
    text = (description or "").strip()
    if len(text) > MAX_DESCRIPTION_CHARS:
        raise ReportTextTooLongError(f"Mô tả tối đa {MAX_DESCRIPTION_CHARS} ký tự")
    if not text and (parsed is None or parsed is ReportType.OTHER):
        raise ReportContentRequiredError()
    return parsed or ReportType.OTHER, text


def parse_resolution(status: str, note: str | None) -> tuple[ReportStatus, str | None]:
    """F14.02 — Chỉ chuyển từ "Mới" sang "Đã xử lý" hoặc "Từ chối", kèm ghi chú tùy chọn."""
    try:
        parsed = ReportStatus(status)
    except ValueError as exc:
        raise InvalidReportStatusError() from exc
    if parsed is ReportStatus.NEW:
        raise InvalidReportStatusError()
    cleaned = (note or "").strip() or None
    if cleaned is not None and len(cleaned) > MAX_NOTE_CHARS:
        raise ReportTextTooLongError(f"Ghi chú tối đa {MAX_NOTE_CHARS} ký tự")
    return parsed, cleaned


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return ZoneInfo("UTC")


def reminder_day_if_due(now: datetime, tz_name: str, reminder_time: time, grace: timedelta) -> date | None:
    """Ngày địa phương cần nhắc nếu `now` nằm trong [giờ nhắc, giờ nhắc + grace] của cùng ngày, hoặc None.

    Quá khung `grace` (ví dụ máy chủ tắt cả ngày) thì bỏ lượt hôm nay thay vì nhắc muộn lúc nửa đêm.
    """
    local = now.astimezone(_zone(tz_name))
    start = datetime.combine(local.date(), reminder_time, tzinfo=local.tzinfo)
    end = min(start + grace, datetime.combine(local.date(), time(23, 59, 59), tzinfo=local.tzinfo))
    return local.date() if start <= local <= end else None


def reminder_message(due_cards: int) -> tuple[str, str]:
    """(tiêu đề, nội dung văn bản thuần) của lời nhắc ôn (F14.04: kèm số thẻ cần ôn)."""
    title = f"Đến giờ ôn tập: còn {due_cards} thẻ"
    body = f"Bạn có {due_cards} thẻ đến hạn cần ôn hôm nay. Vào mục Ôn tập để giữ vững trí nhớ nhé!"
    return title, body


def clip_title(title: str) -> str:
    return title[:MAX_TITLE_CHARS]
