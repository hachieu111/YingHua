from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TypeVar

from app.core.clock import Clock
from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.stats.application.dto import SeriesReadingProgress
from app.modules.stats.application.ports import (
    LearningFactsSource,
    ReadingProgressSource,
    StatsUnitOfWork,
    UserTimezoneSource,
)
from app.modules.stats.application.today_ports import (
    ChapterSuggestionSource,
    WeakWordsSource,
    WeeklyGoalSource,
)
from app.modules.stats.domain.activity import local_date
from app.modules.stats.domain.today import (
    ResumePoint,
    TodayItem,
    TodayRules,
    arrange_items,
    continue_reading_item,
    get_started_item,
    quiz_item,
    review_due_item,
    suggestions_item,
    weekly_goal_item,
)

logger = logging.getLogger(__name__)

READING_SERIES_LIMIT = 20
SUGGESTION_FETCH_LIMIT = 5

_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class TodayPlan:
    items: list[TodayItem]
    all_done: bool  # không có việc nào: giao diện hiện lời chúc đã hoàn thành
    message: str | None
    timezone: str


class GetTodayPlanUseCase:
    """F12.04 — Trang chủ "Hôm nay nên học gì" (US-NH-80).

    Tổng hợp từ F08.01 (thẻ đến hạn), F03.12 (chương đọc dở), F09.01/F08.02 (từ sắp quên), F12.02 (mục tiêu
    tuần) và F10.01 (từ gợi ý). Thứ tự và điều kiện do luật cố định ở domain quyết định; tính khi gọi, không
    lưu bảng. Lỗi ở một nguồn chỉ làm mất thẻ việc đó. Quản trị viên xem của người khác qua `owner_id`
    (F13.07, chỉ đọc).
    """

    def __init__(
        self,
        uow_factory: Callable[[], StatsUnitOfWork],
        facts: LearningFactsSource,
        reading: ReadingProgressSource,
        weak_words: WeakWordsSource,
        goals: WeeklyGoalSource,
        suggestions: ChapterSuggestionSource,
        timezones: UserTimezoneSource,
        rules: TodayRules,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._facts = facts
        self._reading = reading
        self._weak_words = weak_words
        self._goals = goals
        self._suggestion_source = suggestions
        self._timezones = timezones
        self._rules = rules
        self._clock = clock

    async def execute(self, identity: Identity, owner_id: int | None = None) -> TodayPlan:
        user_id = resolve_owner(identity, owner_id)
        now = self._clock.now()
        tz_name = await self._timezones.timezone_of(identity, user_id)
        facts = await _guard("facts", self._facts.facts(identity, user_id))
        progress = await _guard("reading", self._reading.series_progress(user_id, READING_SERIES_LIMIT)) or []
        resume_series = _latest(progress, only_unfinished=True)
        latest_series = _latest(progress, only_unfinished=False)
        items = [
            review_due_item(facts.cards_due, self._rules) if facts else None,
            continue_reading_item(_resume(resume_series)),
            await self._quiz(user_id, now),
            await self._weekly_goal(identity, user_id, tz_name, _resume(resume_series)),
            await self._suggestions(identity, user_id, latest_series),
        ]
        arranged = arrange_items(items, self._rules.max_items)
        if (
            not arranged
            and facts is not None
            and _is_new_learner(facts.words_total, facts.cards_total, progress)
        ):
            arranged = arrange_items([get_started_item()], self._rules.max_items)
        message = None if arranged else "Hôm nay bạn đã hoàn thành. Ghé Thư viện chọn truyện mới nhé!"
        return TodayPlan(arranged, not arranged, message, tz_name)

    async def _quiz(self, user_id: int, now: datetime) -> TodayItem | None:
        weak = await _guard(
            "quiz", self._weak_words.weak_words(user_id, self._rules.quiz_low_retrievability, now)
        )
        return quiz_item(weak.eligible, weak.low, self._rules) if weak else None

    async def _weekly_goal(
        self, identity: Identity, user_id: int, tz_name: str, resume: ResumePoint | None
    ) -> TodayItem | None:
        goal = await _guard("weekly_goal", self._goals.weekly_page_goal(identity, user_id))
        if not goal:
            return None
        today = local_date(self._clock.now(), tz_name)
        monday = today - timedelta(days=today.weekday())
        async with self._uow_factory() as uow:
            days = await uow.activity.between(user_id, monday, today)
        return weekly_goal_item(goal, sum(d.pages_read for d in days), resume)

    async def _suggestions(
        self, identity: Identity, user_id: int, latest: SeriesReadingProgress | None
    ) -> TodayItem | None:
        if latest is None or latest.resume_chapter_id is None:
            return None
        chapter_id = latest.resume_chapter_id
        terms = await _guard(
            "suggestions",
            self._suggestion_source.top_terms(identity, user_id, chapter_id, SUGGESTION_FETCH_LIMIT),
        )
        return suggestions_item(chapter_id, terms or [])


async def _guard(source: str, call: Awaitable[_T]) -> _T | None:
    """Lỗi một nguồn dữ liệu chỉ làm mất thẻ việc đó (ngoại lệ trong F12.04), vẫn ghi log."""
    try:
        return await call
    except Exception:
        logger.exception("Nguồn dữ liệu '%s' của 'Hôm nay nên học gì' bị lỗi", source)
        return None


def _latest(progress: Sequence[SeriesReadingProgress], only_unfinished: bool) -> SeriesReadingProgress | None:
    candidates = [
        p
        for p in progress
        if p.resume_chapter_id is not None
        and p.last_read_at is not None
        and not (only_unfinished and p.completed)
    ]
    return max(candidates, key=_read_time, default=None)


def _read_time(p: SeriesReadingProgress) -> datetime:
    assert p.last_read_at is not None  # đã lọc ở `_latest`
    return p.last_read_at


def _resume(p: SeriesReadingProgress | None) -> ResumePoint | None:
    if p is None or p.resume_chapter_id is None:
        return None
    return ResumePoint(p.series_id, p.title, p.resume_chapter_id, p.resume_page_no)


def _is_new_learner(words_total: int, cards_total: int, progress: Sequence[SeriesReadingProgress]) -> bool:
    return words_total == 0 and cards_total == 0 and not progress
