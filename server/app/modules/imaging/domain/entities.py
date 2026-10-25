"""Thực thể của M04 Xử lý ảnh — thuần Python, không phụ thuộc framework."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# Tăng khi đổi pipeline để ảnh cũ có thể được xử lý lại (F04.14).
PIPELINE_VERSION = "v1"


class TranslationStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ImageVariant(str, Enum):
    """Ba dạng ảnh của một trang (F04.04, F05.01)."""

    ORIGINAL = "original"
    INPAINTED = "inpainted"
    RENDERED = "rendered"


class BubbleClass(str, Enum):
    SPEECH_BUBBLE = "speech_bubble"
    SOUND_EFFECT = "sound_effect"
    CALLIGRAPHY = "calligraphy"
    FLOATING_TEXT = "floating_text"


@dataclass(frozen=True, slots=True)
class NewBubble:
    """Một vùng chữ do pipeline ghi (F04.08–F04.12).

    `tokens` là danh sách `{"word": str, "pinyin": str | None, "entry_id": int | None}`; `lines` là các
    dòng chữ Hán đã gom; `style` là thông tin đắp chữ (màu, cỡ chữ...). Tọa độ tính bằng pixel ảnh gốc.
    """

    idx: int
    class_name: str
    x: int
    y: int
    w: int
    h: int
    text_zh: str
    polygon: Any | None = None
    confidence: float | None = None
    pinyin: str | None = None
    text_vi: str | None = None
    translate_method: str | None = None
    lines: Sequence[Any] = field(default_factory=tuple)
    tokens: Sequence[Any] = field(default_factory=tuple)
    style: Any | None = None


@dataclass(frozen=True, slots=True)
class Bubble:
    id: int
    translation_id: int
    idx: int
    class_name: str
    x: int
    y: int
    w: int
    h: int
    text_zh: str
    polygon: Any | None = None
    confidence: float | None = None
    pinyin: str | None = None
    text_vi: str | None = None
    translate_method: str | None = None
    lines: list[Any] = field(default_factory=list)
    tokens: list[Any] = field(default_factory=list)
    style: Any | None = None


@dataclass(slots=True)
class Translation:
    """Kết quả xử lý một ảnh, đồng thời là một dòng của hàng đợi (F04.07, F04.13)."""

    id: int
    source_file_id: int | None
    sha256: str
    status: TranslationStatus
    pipeline_version: str
    attempts: int
    queued_at: datetime
    phash: int | None = None
    worker_id: str | None = None
    error_step: str | None = None
    error_message: str | None = None
    inpainted_file_id: int | None = None
    rendered_file_id: int | None = None
    stats: dict[str, Any] = field(default_factory=dict)
    processing_ms: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class QueueStats:
    """Số bản dịch theo trạng thái và thời gian xử lý trung bình (F04.05)."""

    counts: dict[str, int]
    avg_processing_ms: int | None
