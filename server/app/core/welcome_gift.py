"""Cổng tặng quà chào mừng cho tài khoản mới (F01.01, F17.03).

M01 khai báo cổng để không phải import M17; M17 hiện thực và `container.py` lắp ghép.
"""

from __future__ import annotations

from typing import Protocol


class WelcomeGiftPort(Protocol):
    async def grant_welcome(self, user_id: int) -> None:
        """Tặng quà chào mừng một lần cho tài khoản vừa tạo. Lỗi do hiện thực tự xử lý hoặc để bên gọi bắt."""
        ...
