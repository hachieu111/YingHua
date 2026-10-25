"""Giọng đọc tiếng Trung của Edge TTS: thông tin hiển thị và danh sách mặc định khi dịch vụ lỗi (F11.03)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

VOICES_TTL = timedelta(hours=24)  # danh sách giọng của dịch vụ hiếm khi đổi
FAILURE_TTL = timedelta(minutes=5)  # dịch vụ lỗi: dùng danh sách mặc định, thử gọi lại sau ít phút
LOCALE_PREFIX = "zh-"

_LOCALE_LABELS = {
    "zh-CN": "Trung Quốc đại lục",
    "zh-TW": "Đài Loan",
    "zh-HK": "Hồng Kông",
}
_GENDER_LABELS = {"female": "nữ", "male": "nam"}


@dataclass(frozen=True, slots=True)
class VoiceInfo:
    short_name: str  # vd. zh-CN-XiaoxiaoNeural, dùng làm `tts_voice` và tham số `voice`
    locale: str
    gender: str  # female | male
    friendly_name: str  # tiếng Việt, vd. "Xiaoxiao (giọng nữ, Trung Quốc đại lục)"


def friendly_name(short_name: str, locale: str, gender: str) -> str:
    """Tên dễ đọc bằng tiếng Việt dựng từ tên ngắn: bỏ tiền tố vùng và hậu tố Neural."""
    name = short_name.rsplit("-", 1)[-1].removesuffix("Neural") or short_name
    kind = _GENDER_LABELS.get(gender.lower(), "")
    region = _LOCALE_LABELS.get(locale, locale)
    detail = ", ".join(part for part in (f"giọng {kind}" if kind else "", region) if part)
    return f"{name} ({detail})"


def make_voice(short_name: str, locale: str, gender: str) -> VoiceInfo:
    gender = gender.lower()
    return VoiceInfo(short_name, locale, gender, friendly_name(short_name, locale, gender))


def voices_from_service(raw: Iterable[Mapping[str, Any]]) -> list[VoiceInfo]:
    """Giọng tiếng Trung (zh-*) từ phản hồi của dịch vụ; mục thiếu trường hoặc sai kiểu bị bỏ qua."""
    voices: dict[str, VoiceInfo] = {}
    for item in raw:
        short, locale, gender = item.get("ShortName"), item.get("Locale"), item.get("Gender")
        if not all(isinstance(v, str) and v for v in (short, locale, gender)):
            continue
        if str(locale).startswith(LOCALE_PREFIX):
            voices.setdefault(str(short), make_voice(str(short), str(locale), str(gender)))
    return sorted(voices.values(), key=lambda v: (v.locale, v.short_name))


# Danh sách mặc định khớp `KNOWN_VOICES` của rules.py; dùng khi dịch vụ không trả được danh sách.
DEFAULT_VOICES: tuple[VoiceInfo, ...] = tuple(
    make_voice(short, short[:5], gender)
    for short, gender in (
        ("zh-CN-XiaoxiaoNeural", "female"),
        ("zh-CN-XiaoyiNeural", "female"),
        ("zh-CN-YunxiNeural", "male"),
        ("zh-CN-YunjianNeural", "male"),
        ("zh-CN-YunxiaNeural", "male"),
        ("zh-CN-YunyangNeural", "male"),
        ("zh-CN-liaoning-XiaobeiNeural", "female"),
        ("zh-CN-shaanxi-XiaoniNeural", "female"),
        ("zh-TW-HsiaoChenNeural", "female"),
        ("zh-TW-HsiaoYuNeural", "female"),
        ("zh-TW-YunJheNeural", "male"),
        ("zh-HK-HiuGaaiNeural", "female"),
        ("zh-HK-HiuMaanNeural", "female"),
        ("zh-HK-WanLungNeural", "male"),
    )
)
