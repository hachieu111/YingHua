"""Bộ lập lịch FSRS: bọc thư viện `fsrs` để domain/application không phụ thuộc vào nó."""

from __future__ import annotations

from datetime import datetime

from fsrs import Card as FsrsCard
from fsrs import Rating as FsrsRating
from fsrs import Scheduler
from fsrs import State as FsrsState

from app.modules.review.domain.entities import CardState, Rating, SchedulingState
from app.modules.review.domain.fsrs_profile import FsrsProfile

_STATE_TO_FSRS = {
    CardState.LEARNING: FsrsState.Learning,
    CardState.REVIEW: FsrsState.Review,
    CardState.RELEARNING: FsrsState.Relearning,
}
_STATE_FROM_FSRS = {v: k for k, v in _STATE_TO_FSRS.items()}
_RATING_TO_FSRS = {
    Rating.AGAIN: FsrsRating.Again,
    Rating.HARD: FsrsRating.Hard,
    Rating.GOOD: FsrsRating.Good,
    Rating.EASY: FsrsRating.Easy,
}

# Thẻ không cần mã riêng trong thư viện (ta giữ trạng thái ở CSDL); mã cố định tránh việc thư viện
# tạo mã từ đồng hồ và ngủ 1 ms mỗi lần.
_NO_CARD_ID = 0


class FsrsScheduler:
    """Tham số mặc định của thư viện; có `profile` riêng của người học (F08.08) thì dùng tham số đó.

    `enable_fuzzing` làm lệch khoảng cách ôn ngẫu nhiên nhẹ để thẻ không dồn cùng ngày; test tắt đi để
    kết quả xác định.
    """

    def __init__(self, desired_retention: float = 0.9, enable_fuzzing: bool = True) -> None:
        self._enable_fuzzing = enable_fuzzing
        self._scheduler = Scheduler(desired_retention=desired_retention, enable_fuzzing=enable_fuzzing)

    def new_state(self, now: datetime) -> SchedulingState:
        return _from_fsrs(FsrsCard(card_id=_NO_CARD_ID, due=now))

    def review(
        self, state: SchedulingState, rating: Rating, now: datetime, profile: FsrsProfile | None = None
    ) -> SchedulingState:
        scheduler = self._scheduler_for(profile)
        card = FsrsCard(
            card_id=_NO_CARD_ID,
            state=_STATE_TO_FSRS[state.state],
            step=state.step,
            stability=state.stability,
            difficulty=state.difficulty,
            due=state.due_at,
            last_review=state.last_review_at,
        )
        updated, _ = scheduler.review_card(card, _RATING_TO_FSRS[rating], review_datetime=now)
        return _from_fsrs(updated)

    def _scheduler_for(self, profile: FsrsProfile | None) -> Scheduler:
        if profile is None:
            return self._scheduler
        return Scheduler(
            parameters=profile.weights,
            desired_retention=profile.desired_retention,
            enable_fuzzing=self._enable_fuzzing,
        )

    def retrievability(self, state: SchedulingState, now: datetime) -> float:
        card = FsrsCard(
            card_id=_NO_CARD_ID,
            state=_STATE_TO_FSRS[state.state],
            step=state.step,
            stability=state.stability,
            difficulty=state.difficulty,
            due=state.due_at,
            last_review=state.last_review_at,
        )
        return float(self._scheduler.get_card_retrievability(card, now))


def _from_fsrs(card: FsrsCard) -> SchedulingState:
    return SchedulingState(
        state=_STATE_FROM_FSRS[card.state],
        step=card.step,
        stability=card.stability,
        difficulty=card.difficulty,
        due_at=card.due,
        last_review_at=card.last_review,
    )
