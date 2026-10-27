"""Tham số FSRS riêng của từng người học (F08.08) — thuần Python."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.modules.review.domain.entities import Rating

FSRS_PARAMETER_COUNT = 21
DESIRED_RETENTION_MIN = 0.80
DESIRED_RETENTION_MAX = 0.97
DEFAULT_DESIRED_RETENTION = 0.90
# Đã tối ưu rồi thì chỉ tối ưu lại khi có thêm chừng này lượt ôn mới (tránh tính lại vô ích mỗi tuần).
MIN_NEW_REVIEWS_BEFORE_REOPTIMIZE = 50
# Chỉ lấy các lượt ôn gần nhất để thời gian tối ưu một người không vượt quá khóa của tác vụ nền.
MAX_OPTIMIZER_LOGS = 20000
# Khoảng ôn mô phỏng sau chuỗi "Được" liên tiếp phải nằm trong miền hợp lý (ngày).
SANITY_STEPS = 6
SANITY_MIN_INTERVAL_DAYS = 1.0
SANITY_MAX_INTERVAL_DAYS = 3650.0


@dataclass(frozen=True, slots=True)
class FsrsProfile:
    """Bộ trọng số 21 số và độ nhớ mong muốn của một người học."""

    weights: tuple[float, ...]
    desired_retention: float = DEFAULT_DESIRED_RETENTION


@dataclass(frozen=True, slots=True)
class OptimizerLog:
    """Một lượt ôn dùng làm dữ liệu huấn luyện."""

    card_id: int
    rating: Rating
    reviewed_at: datetime
    duration_ms: int | None


class FsrsOptimizerUnavailableError(Exception):
    """Bộ tối ưu không dùng được trong môi trường này (thiếu torch/pandas/tqdm). Không lộ ra API."""


class InvalidFsrsParametersError(Exception):
    """Tham số mới ngoài miền cho phép hoặc làm lịch ôn bất thường: giữ tham số cũ (F08.08)."""
