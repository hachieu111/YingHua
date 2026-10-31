"""Cổng hỏi quyền đọc truyện VIP (F17.05, F03.10).

M03 khai báo cổng này để hỏi "người này có đọc được các chương không đọc thử của truyện VIP không" mà không
phụ thuộc M17; M17 hiện thực (`SqlVipAccess`). Trạng thái VIP tính theo `now` mỗi lần hỏi, không có job đổi
trạng thái (F17.03).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ViewerVipState:
    """Quyền VIP của một người tại thời điểm hỏi."""

    is_vip: bool = False  # hạn VIP còn lớn hơn thời điểm hỏi
    ticket_balance: int = 0  # để báo "còn vé hay không" khi từ chối (VIP_REQUIRED)
    unlocked_series_ids: frozenset[int] = frozenset()  # trong số các truyện được hỏi, truyện đã mở bằng vé

    def can_read(self, series_id: int) -> bool:
        return self.is_vip or series_id in self.unlocked_series_ids


class VipAccessPort(Protocol):
    async def viewer_state(
        self, user_id: int, series_ids: Sequence[int], now: datetime
    ) -> ViewerVipState: ...
