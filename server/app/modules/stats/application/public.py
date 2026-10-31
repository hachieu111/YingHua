"""Bề mặt công khai của M12 cho module khác: ghi hoạt động học trong cùng giao dịch với hành động (F12.01).

Module khác (M03, M07, M08, M09) gắn `ActivityRecorder` vào Unit of Work của mình (cùng phiên) rồi gọi
`record(...)` ngay trước `commit()`; nhờ vậy hành động và bộ đếm commit hoặc hủy cùng nhau.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.modules.stats.domain.activity import ActivityDelta, local_date, study_seconds_from_ms
from app.modules.stats.domain.streak import StreakResult, compute_streak


class ActivityRecorder(Protocol):
    async def record(self, user_id: int, at: datetime, delta: ActivityDelta) -> None:
        """Cộng `delta` vào ngày của `at` theo múi giờ của người học."""
        ...


# `compute_streak` và `local_date` cho M16 (F16.06): cùng quy tắc chuỗi ngày và ngày địa phương với F12.02.
__all__ = [
    "ActivityDelta",
    "ActivityRecorder",
    "StreakResult",
    "compute_streak",
    "local_date",
    "study_seconds_from_ms",
]
