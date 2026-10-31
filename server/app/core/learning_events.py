"""Cổng báo sự kiện học để cộng XP (F16.02).

M03, M07, M08, M09 và mini-game gọi cổng này trong CÙNG giao dịch với hành động học, sau khi bộ đếm
`daily_activities` đã được cập nhật. M16 hiện thực cổng (gắn vào Unit of Work của module nguồn, cùng phiên),
nên module nguồn không phải import M16 và không có vòng phụ thuộc (cùng cách làm với `AiPolicy`).
Trình duyệt không có API nào để gửi XP: chỉ use case phía máy chủ mới tạo `LearningEvent`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol


class LearningSource(str, Enum):
    PAGE_READ = "page_read"  # đọc một trang lần đầu (F03.12)
    REVIEW = "review"  # một lượt chấm thẻ hợp lệ (F08.02)
    WORD_SAVED = "word_saved"  # tạo mục từ mới trong Sổ tay (F07.01)
    QUIZ = "quiz"  # nộp bài kiểm tra (F09.02)
    MINIGAME = "minigame"  # nộp ván mini-game (F16.01)


@dataclass(frozen=True, slots=True)
class LearningEvent:
    """Một hoạt động học do máy chủ ghi nhận.

    `ref` là mã tham chiếu của nguồn (mã trang, mã lượt ôn, từ, mã bài, mã ván) làm khóa chống trùng.
    Số liệu kèm theo: bài kiểm tra dùng `value` = số câu đúng, `answered`, `total`;
    mini-game dùng `value` = điểm.
    """

    user_id: int
    source: LearningSource
    ref: str
    at: datetime
    value: int = 0
    answered: int = 0
    total: int = 0


class LearningSignal(str, Enum):
    """Hành động không sinh XP nhưng làm đổi chỉ số huy hiệu (F16.11); đánh giá ngay sau khi lưu."""

    VOCAB_MASTERED = "vocab_mastered"  # mục từ vừa chuyển sang "Đã thuộc" (huy hiệu hsk3_master)
    BUBBLE_LOOKUP = "bubble_lookup"  # tra/hover bong bóng mới (huy hiệu apprentice_translator)


class LearningEventPort(Protocol):
    async def record(self, event: LearningEvent) -> int:
        """Ghi sự kiện XP trong giao dịch hiện tại. Trả số XP thực nhận (0 nếu trùng hoặc chạm trần)."""
        ...

    async def signal(self, user_id: int, signal: LearningSignal, at: datetime) -> None:
        """Xếp hàng việc đánh giá huy hiệu theo chỉ số; chạy ở `after_commit`, không làm hỏng hành động."""
        ...

    async def after_commit(self) -> None:
        """Đánh giá huy hiệu đã xếp hàng và gửi thông báo. Gọi SAU `commit()`; lỗi chỉ ghi log WARNING."""
        ...


class NoopLearningEvents:
    """Không làm gì; dùng khi không cần XP (vd. test đơn vị của module nguồn)."""

    async def record(self, event: LearningEvent) -> int:
        return 0

    async def signal(self, user_id: int, signal: LearningSignal, at: datetime) -> None:
        return None

    async def after_commit(self) -> None:
        return None
