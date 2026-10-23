"""Lập lịch ôn tập SM-2 (SuperMemo 2) với 4 mức đánh giá.

rating: 1=Again (quên) | 2=Hard | 3=Good | 4=Easy  ->  chất lượng SM-2 q = 1 | 3 | 4 | 5
- Again: lapses+1 (nếu đang ôn), reps=0, hẹn lại sau 10 phút, EF -0.2 (tối thiểu 1.3)
- Đúng: EF' = EF + (0.1 - (5-q)(0.08 + (5-q)0.02)), khoảng cách I1=1, I2=6, In=I(n-1)*EF
  Hard nhân thêm 0.8 (ít nhất +1 ngày so với lần trước khi đã qua 2 lần), Easy nhân thêm 1.3.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

MIN_EASE = 1.3
AGAIN_MINUTES = 10
QUALITY = {2: 3, 3: 4, 4: 5}


@dataclass
class Schedule:
    state: str
    interval_days: float
    ease_factor: float
    reps: int
    lapses: int
    due_at: datetime


def next_schedule(*, state: str, interval_days: float, ease_factor: float, reps: int, lapses: int,
                  rating: int, now: datetime) -> Schedule:
    if rating not in (1, 2, 3, 4):
        raise ValueError("rating phải từ 1 đến 4")

    if rating == 1:
        ease = max(MIN_EASE, ease_factor - 0.2)
        new_state = "relearning" if state == "review" else "learning"
        return Schedule(state=new_state, interval_days=AGAIN_MINUTES / 1440, ease_factor=ease, reps=0,
                        lapses=lapses + (1 if state == "review" else 0),
                        due_at=now + timedelta(minutes=AGAIN_MINUTES))

    q = QUALITY[rating]
    ease = max(MIN_EASE, ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
    if reps == 0:
        interval = 1.0
    elif reps == 1:
        interval = 6.0
    else:
        interval = max(interval_days, 1.0) * ease
    if rating == 2:
        interval = max(1.0, interval * 0.8) if reps < 2 else max(interval_days + 1, interval * 0.8)
    elif rating == 4:
        interval *= 1.3
    interval = round(interval, 2)
    return Schedule(state="review", interval_days=interval, ease_factor=round(ease, 3), reps=reps + 1,
                    lapses=lapses, due_at=now + timedelta(days=interval))
