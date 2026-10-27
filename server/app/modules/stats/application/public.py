"""Bề mặt công khai của M12 cho module khác: ghi hoạt động học trong cùng giao dịch với hành động (F12.01).

Module khác (M03, M07, M08, M09) gắn `ActivityRecorder` vào Unit of Work của mình (cùng phiên) rồi gọi
`record(...)` ngay trước `commit()`; nhờ vậy hành động và bộ đếm commit hoặc hủy cùng nhau.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.modules.stats.domain.activity import ActivityDelta, study_seconds_from_ms


class ActivityRecorder(Protocol):
    async def record(self, user_id: int, at: datetime, delta: ActivityDelta) -> None:
        """Cộng `delta` vào ngày của `at` theo múi giờ của người học."""
        ...


__all__ = ["ActivityDelta", "ActivityRecorder", "study_seconds_from_ms"]
