"""Gộp các lời gọi trùng khóa đang chạy cùng lúc: chỉ một lời gọi thật, mọi bên chờ nhận cùng kết quả.

Dùng cho việc tốn kém hoặc tính phí (vd. gọi Edge TTS, F11.05). Chỉ có tác dụng trong một tiến trình;
giữa nhiều tiến trình cần ràng buộc UNIQUE ở CSDL.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


class SingleFlight:
    def __init__(self) -> None:
        self._inflight: dict[str, asyncio.Task[Any]] = {}

    @property
    def pending(self) -> int:
        """Số khóa đang chạy (để test kiểm tra đã dọn)."""
        return len(self._inflight)

    async def run(self, key: str, factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
        task = self._inflight.get(key)
        if task is None:
            task = asyncio.ensure_future(factory())
            self._inflight[key] = task
            task.add_done_callback(lambda done: self._finish(key, done))
        # shield: một bên chờ bị hủy (khách ngắt kết nối) không làm hỏng việc của các bên còn lại.
        result: T = await asyncio.shield(task)
        return result

    def _finish(self, key: str, task: asyncio.Task[Any]) -> None:
        if self._inflight.get(key) is task:
            del self._inflight[key]
        if not task.cancelled():
            task.exception()  # đánh dấu đã đọc lỗi, tránh cảnh báo "exception never retrieved"
