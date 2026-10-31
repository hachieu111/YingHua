"""Bản giả của `ActivityRecorder` (M12) và kho tham số FSRS (M08) cho test đơn vị."""

from __future__ import annotations

from datetime import datetime

from app.core.learning_events import LearningEvent, LearningSignal
from app.modules.review.domain.fsrs_profile import FsrsProfile
from app.modules.stats.domain.activity import ActivityDelta


class FakeActivity:
    """Ghi lại các lần cộng bộ đếm để test kiểm "hành động có ghi hoạt động ngày"."""

    def __init__(self) -> None:
        self.records: list[tuple[int, datetime, ActivityDelta]] = []

    async def record(self, user_id: int, at: datetime, delta: ActivityDelta) -> None:
        self.records.append((user_id, at, delta))

    def total(self, field: str) -> int:
        return sum(getattr(delta, field) for _, _, delta in self.records)


class FakeLearning:
    """Bản giả của `LearningEventPort` (M16): ghi lại sự kiện XP mà use case của module nguồn báo lên."""

    def __init__(self) -> None:
        self.events: list[LearningEvent] = []
        self.signals: list[tuple[int, LearningSignal]] = []
        self.after_commit_calls = 0

    async def record(self, event: LearningEvent) -> int:
        self.events.append(event)
        return 0

    async def signal(self, user_id: int, signal: LearningSignal, at: datetime) -> None:
        self.signals.append((user_id, signal))

    async def after_commit(self) -> None:
        self.after_commit_calls += 1


class FakeFsrsProfiles:
    def __init__(self) -> None:
        self.profiles: dict[int, FsrsProfile] = {}
        self.review_counts: dict[int, int] = {}
        self.candidates: list[int] = []
        self.last_query: tuple[int, int, datetime, int] | None = None

    async def get(self, user_id: int) -> FsrsProfile | None:
        return self.profiles.get(user_id)

    async def save(self, user_id: int, profile: FsrsProfile, review_count: int, now: datetime) -> None:
        self.profiles[user_id] = profile
        self.review_counts[user_id] = review_count

    async def users_to_optimize(
        self, min_reviews: int, min_new_reviews: int, stale_before: datetime, limit: int
    ) -> list[int]:
        self.last_query = (min_reviews, min_new_reviews, stale_before, limit)
        return self.candidates[:limit]
