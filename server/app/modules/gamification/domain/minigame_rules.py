"""Quy tắc chung của mini-game (F16.01): hạn nộp lượt, dọn lượt cũ, bộ thủ yếu. Không dùng AI."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.modules.gamification.domain.entities import HanziRadicalInfo

GAME_TYPE = "pinyin_blade"
GAME_SECONDS = 120
DURATION_TOLERANCE_MS = 5000  # độ trễ mạng/đồng hồ cho phép khi nộp
MIN_DURATION_MS = 1000
MAX_DURATION_MS = GAME_SECONDS * 1000 + DURATION_TOLERANCE_MS
ROUND_SUBMIT_GRACE_SECONDS = 60  # từ lúc phát lượt: màn mở đầu + mạng + thời gian chơi mới phải nộp xong
ROUND_RETENTION_DAYS = 7  # lượt đã phát giữ tối đa chừng này ngày rồi bị dọn (F15.03)
ROUND_PURGE_BATCH_SIZE = 1000
ROUND_PURGE_MAX_BATCHES = 50  # chặn một lần chạy quá lâu; phần còn lại dọn ở lần sau
WEAK_LOOKBACK_DAYS = 30
WEAK_MIN_COUNT = 3
WEAK_MAX_RADICALS = 3
NO_DATA_MESSAGE = "Chưa có dữ liệu để gợi ý bộ thủ yếu"
HSK_LEVEL_MARGIN = 1  # chữ HSK cấp không vượt quá trình độ + 1
DEFAULT_HSK_LEVEL = 1


def round_deadline(issued_at: datetime) -> datetime:
    """Hạn nộp kết quả của một lượt: thời gian chơi cộng khoảng dự phòng."""
    return issued_at + timedelta(seconds=GAME_SECONDS + ROUND_SUBMIT_GRACE_SECONDS)


def server_duration_ms(issued_at: datetime, submitted_at: datetime) -> int:
    """Thời gian trôi qua theo đồng hồ máy chủ kể từ lúc phát lượt (không âm, không chặn trần)."""
    return max(0, int((submitted_at - issued_at).total_seconds() * 1000))


@dataclass(frozen=True, slots=True)
class WeakRadical:
    radical: str
    count: int


def weak_radicals(char_counts: Mapping[str, int], infos: Mapping[str, HanziRadicalInfo]) -> list[WeakRadical]:
    """Đếm bộ thủ/thành phần theo số lần quên hoặc khó của các chữ, lấy tối đa 3 bộ thủ đạt ngưỡng tối thiểu.

    Mỗi lần xuất hiện của một chữ tính 1 cho mỗi bộ thủ/thành phần khác nhau của chữ đó.
    """
    totals: Counter[str] = Counter()
    for ch, n in char_counts.items():
        info = infos.get(ch)
        if info is None:
            continue
        for part in info.parts:
            totals[part] += n
    ranked = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    return [WeakRadical(r, c) for r, c in ranked if c >= WEAK_MIN_COUNT][:WEAK_MAX_RADICALS]


def max_hsk_level(user_level: int | None) -> int:
    return (user_level if user_level is not None else DEFAULT_HSK_LEVEL) + HSK_LEVEL_MARGIN
