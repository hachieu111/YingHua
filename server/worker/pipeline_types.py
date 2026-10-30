"""Kiểu dữ liệu vào/ra của adapter pipeline ảnh và lỗi theo từng bước.

Mọi trường (trừ ảnh) đều là kiểu JSON thuần để worker ghi thẳng vào CSDL.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np
import numpy.typing as npt

ImageArray = npt.NDArray[np.uint8]
PipelineStep = Literal["detect", "ocr", "segment", "translate", "inpaint", "render"]


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Đường dẫn tài nguyên của module xử lý ảnh; worker lắp từ Settings."""

    pipeline_dir: Path
    yolo_model_path: Path
    font_dir: Path
    xianxia_dict_dir: Path


@dataclass(slots=True)
class BubbleResult:
    """Một bong bóng đã nhận diện + dịch; `tokens` chưa có `entry_id` (worker tra sau)."""

    idx: int
    class_name: str
    x: int
    y: int
    w: int
    h: int
    polygon: Any
    confidence: float | None
    text_zh: str
    pinyin: str
    text_vi: str
    translate_method: str
    lines: list[dict[str, Any]] = field(default_factory=list)
    tokens: list[dict[str, Any]] = field(default_factory=list)
    style: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Dạng dict JSON thuần để lưu CSDL."""
        return asdict(self)


@dataclass(slots=True)
class TextPhaseResult:
    """Giai đoạn 1 (detect + OCR + dịch + tách từ): bong bóng chưa có `style`, ghi được ngay để người học đọc.

    `state` là dữ liệu trung gian riêng của adapter, chỉ để đưa lại cho `process_images`.
    """

    bubbles: list[BubbleResult]
    mode: str | None
    stats: dict[str, Any]
    state: Any = field(default=None, repr=False)


@dataclass(slots=True)
class ImagePhaseResult:
    """Giai đoạn 2 (xóa chữ + đắp chữ + style): ảnh dẫn xuất, `styles` theo `idx` bong bóng, thống kê đủ."""

    inpainted: ImageArray
    rendered: ImageArray
    styles: dict[int, dict[str, Any] | None]
    stats: dict[str, Any]


@dataclass(slots=True)
class PipelineResult:
    """Kết quả xử lý một trang (cả hai giai đoạn gộp lại)."""

    bubbles: list[BubbleResult]
    inpainted: ImageArray
    rendered: ImageArray
    mode: str | None
    stats: dict[str, Any]


class PipelineStepError(Exception):
    """Lỗi ở một bước pipeline; `message` tiếng Việt, an toàn để hiện cho người dùng (không stack trace)."""

    def __init__(self, step: PipelineStep, message: str) -> None:
        super().__init__(f"[{step}] {message}")
        self.step: PipelineStep = step
        self.message = message
