"""Cài đặt cá nhân (M02). Các trường của module khác (tốc độ đọc, nhắc ôn...) có trong bảng nhưng
chỉ được mở qua API khi module tương ứng được xây dựng."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.core.errors import InvalidInputError

HSK_MIN, HSK_MAX = 1, 9
WEEKLY_PAGE_GOAL_MAX = 1000
_VOICE_PATTERN = re.compile(r"^[a-z]{2,3}-[A-Z]{2}-[A-Za-z0-9]{1,40}$")
DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"
BUBBLE_FONT_SCALE_MIN, BUBBLE_FONT_SCALE_MAX = 80, 160
BUBBLE_FONT_SCALE_STEP = 10
DEFAULT_BUBBLE_FONT_SCALE = 100


class ReadingMode(str, Enum):
    READ = "read"
    LEARN = "learn"


class LearningGoal(str, Enum):
    STUDY = "study"
    ENTERTAINMENT = "entertainment"
    BOTH = "both"


@dataclass(slots=True)
class UserSettings:
    user_id: int
    hsk_level: int | None = None  # None nghĩa là "Chưa chọn"
    default_mode: ReadingMode = ReadingMode.READ
    tts_voice: str | None = None
    learning_goal: LearningGoal | None = None
    weekly_page_goal: int | None = None
    timezone: str = DEFAULT_TIMEZONE
    show_xianxia: bool = True  # F06.03: hiện nghĩa từ điển tu tiên
    bubble_font_scale: int = DEFAULT_BUBBLE_FONT_SCALE  # F02.04: cỡ chữ lớp dịch, phần trăm


EDITABLE_FIELDS = frozenset(
    {
        "hsk_level",
        "default_mode",
        "tts_voice",
        "learning_goal",
        "weekly_page_goal",
        "show_xianxia",
        "bubble_font_scale",
    }
)


def _invalid(field: str) -> InvalidInputError:
    return InvalidInputError(f"Giá trị không hợp lệ: {field}", details={"field": field})


def apply_changes(settings: UserSettings, changes: Mapping[str, Any]) -> None:
    """Kiểm tra rồi áp dụng các thay đổi (F02.01–F02.03). Chỉ trường có trong `changes` được đổi."""
    unknown = set(changes) - EDITABLE_FIELDS
    if unknown:
        raise _invalid(sorted(unknown)[0])
    if "hsk_level" in changes:
        value = changes["hsk_level"]
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or not HSK_MIN <= value <= HSK_MAX
        ):
            raise _invalid("hsk_level")
        settings.hsk_level = value
    if "default_mode" in changes:
        try:
            settings.default_mode = ReadingMode(changes["default_mode"])
        except ValueError as exc:
            raise _invalid("default_mode") from exc
    if "tts_voice" in changes:
        voice = changes["tts_voice"]
        # TODO(F02.03): đối chiếu với danh sách giọng thật của Edge TTS khi có M11.
        if voice is not None and not _VOICE_PATTERN.match(str(voice)):
            raise _invalid("tts_voice")
        settings.tts_voice = voice
    if "learning_goal" in changes:
        goal = changes["learning_goal"]
        try:
            settings.learning_goal = None if goal is None else LearningGoal(goal)
        except ValueError as exc:
            raise _invalid("learning_goal") from exc
    if "weekly_page_goal" in changes:
        pages = changes["weekly_page_goal"]
        if pages is not None and (
            not isinstance(pages, int) or isinstance(pages, bool) or not 1 <= pages <= WEEKLY_PAGE_GOAL_MAX
        ):
            raise _invalid("weekly_page_goal")
        settings.weekly_page_goal = pages
    if "show_xianxia" in changes:
        flag = changes["show_xianxia"]
        if not isinstance(flag, bool):
            raise _invalid("show_xianxia")
        settings.show_xianxia = flag
    if "bubble_font_scale" in changes:
        scale = changes["bubble_font_scale"]
        valid = (
            isinstance(scale, int)
            and not isinstance(scale, bool)
            and BUBBLE_FONT_SCALE_MIN <= scale <= BUBBLE_FONT_SCALE_MAX
            and scale % BUBBLE_FONT_SCALE_STEP == 0
        )
        if not valid:
            raise InvalidInputError(
                f"Cỡ chữ bong bóng phải từ {BUBBLE_FONT_SCALE_MIN} đến {BUBBLE_FONT_SCALE_MAX}%, "
                f"bước {BUBBLE_FONT_SCALE_STEP}%",
                details={"field": "bubble_font_scale"},
            )
        settings.bubble_font_scale = scale
