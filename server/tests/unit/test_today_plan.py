"""F12.04 / US-NH-80 — luật chọn, thứ tự và ngưỡng của việc hôm nay, dùng nguồn giả."""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import TracebackType
from typing import Any

from app.modules.auth.application.public import Identity, Role
from app.modules.stats.application.dto import LearningFacts, SeriesReadingProgress
from app.modules.stats.application.today_ports import WeakWords
from app.modules.stats.application.use_cases.get_today_plan import GetTodayPlanUseCase
from app.modules.stats.domain.activity import DayActivity
from app.modules.stats.domain.today import TodayKind, TodayRules
from tests.conftest import FixedClock

NOW = datetime(2026, 10, 25, 3, 0, tzinfo=timezone.utc)  # Chủ nhật; giờ VN 10:00
RULES = TodayRules(20, 5, 0.7, 5, 10)
USER = Identity(1, Role.USER, "s")
NO_WEAK = WeakWords(0, 0)


def _facts(due: int = 0, words: int = 3, cards: int = 9) -> LearningFacts:
    return LearningFacts(words, 0, words, 0, cards, due, 0, 0, 0)


def _series(series_id: int, at: datetime, completed: bool = False) -> SeriesReadingProgress:
    return SeriesReadingProgress(
        series_id, f"Truyện {series_id}", None, 1, 10, 10, at, series_id * 10, 2, completed
    )


class _Facts:
    def __init__(self, facts: LearningFacts | Exception) -> None:
        self.value = facts

    async def facts(self, identity: Identity, user_id: int) -> LearningFacts:
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


class _Reading:
    def __init__(self, items: list[SeriesReadingProgress]) -> None:
        self.items = items

    async def series_progress(self, user_id: int, limit: int) -> list[SeriesReadingProgress]:
        return self.items


class _Weak:
    def __init__(self, weak: WeakWords) -> None:
        self.weak = weak

    async def weak_words(self, user_id: int, threshold: float, now: datetime) -> WeakWords:
        return self.weak


class _Goal:
    def __init__(self, goal: int | None) -> None:
        self.goal = goal

    async def weekly_page_goal(self, identity: Identity, owner_id: int) -> int | None:
        return self.goal


class _Terms:
    def __init__(self, terms: list[str]) -> None:
        self.terms = terms
        self.chapters: list[int] = []

    async def top_terms(self, identity: Identity, owner_id: int, chapter_id: int, limit: int) -> list[str]:
        self.chapters.append(chapter_id)
        return self.terms


class _Zone:
    async def timezone_of(self, identity: Identity, owner_id: int) -> str:
        return "Asia/Ho_Chi_Minh"


class _Activity:
    def __init__(self, pages: int) -> None:
        self.pages = pages

    async def between(self, user_id: int, start: date, end: date) -> list[DayActivity]:
        return [DayActivity(end, 0, self.pages, 0, 0, 0)]


class _Uow:
    def __init__(self, pages: int) -> None:
        self.activity = _Activity(pages)

    async def __aenter__(self) -> _Uow:
        return self

    async def __aexit__(
        self, et: type[BaseException] | None, e: BaseException | None, tb: TracebackType | None
    ) -> None:
        return None


def _use_case(
    facts: LearningFacts | Exception | None = None,
    reading: list[SeriesReadingProgress] | None = None,
    weak: WeakWords = NO_WEAK,
    goal: int | None = None,
    pages: int = 0,
    terms: list[str] | None = None,
    rules: TodayRules = RULES,
) -> tuple[GetTodayPlanUseCase, _Terms]:
    source = _Terms(terms or [])
    use_case = GetTodayPlanUseCase(
        lambda: _Uow(pages),  # type: ignore[arg-type, return-value]
        _Facts(facts if facts is not None else _facts()),
        _Reading(reading or []),
        _Weak(weak),
        _Goal(goal),
        source,
        _Zone(),
        rules,
        FixedClock(NOW),
    )
    return use_case, source


def _kinds(plan: Any) -> list[TodayKind]:
    return [i.kind for i in plan.items]


async def test_today_items_follow_fixed_order_and_skip_inapplicable() -> None:
    """US-NH-80 TC1: thứ tự cố định, chỉ hiện việc thỏa điều kiện."""
    reading = [_series(1, NOW)]
    use_case, _ = _use_case(
        _facts(due=3), reading, WeakWords(12, 6), goal=10, pages=4, terms=["你好", "朋友"]
    )
    plan = await use_case.execute(USER)
    assert _kinds(plan) == [
        TodayKind.REVIEW_DUE,
        TodayKind.CONTINUE_READING,
        TodayKind.TAKE_QUIZ,
        TodayKind.WEEKLY_GOAL,
        TodayKind.CHAPTER_SUGGESTIONS,
    ]
    assert [i.priority for i in plan.items] == [1, 2, 3, 4, 5]
    assert not plan.all_done
    use_case, _ = _use_case(_facts(due=0), reading)
    assert _kinds(await use_case.execute(USER)) == [TodayKind.CONTINUE_READING]


async def test_review_item_is_urgent_only_from_threshold() -> None:
    """US-NH-80 TC2: từ 20 thẻ trở lên thì đánh dấu ưu tiên."""
    below, _ = _use_case(_facts(due=19))
    at, _ = _use_case(_facts(due=20))
    assert (await below.execute(USER)).items[0].urgent is False
    first = (await at.execute(USER)).items[0]
    assert first.urgent and first.count == 20 and first.action.type == "review" and first.action.deck == "all"


async def test_quiz_item_needs_enough_words_and_enough_weak_words() -> None:
    """US-NH-80 TC3: đủ điều kiện ra đề (>= 10 từ) và >= 5 từ độ nhớ thấp."""
    for weak, expected in [(WeakWords(12, 5), True), (WeakWords(12, 4), False), (WeakWords(9, 9), False)]:
        use_case, _ = _use_case(_facts(due=0), weak=weak)
        assert (TodayKind.TAKE_QUIZ in _kinds(await use_case.execute(USER))) is expected


async def test_weekly_goal_shows_remaining_pages_only_when_not_reached() -> None:
    """US-NH-80 TC4: ghi rõ số trang còn thiếu; đạt mục tiêu hoặc chưa đặt thì không hiện."""
    reading = [_series(1, NOW)]
    short, _ = _use_case(_facts(), reading, goal=10, pages=4)
    item = next(i for i in (await short.execute(USER)).items if i.kind is TodayKind.WEEKLY_GOAL)
    assert item.count == 6 and "6 trang" in item.message
    assert item.action.type == "reader" and item.action.chapter_id == 10
    for goal, pages in [(10, 10), (None, 0)]:
        use_case, _ = _use_case(_facts(), reading, goal=goal, pages=pages)
        assert TodayKind.WEEKLY_GOAL not in _kinds(await use_case.execute(USER))


async def test_reading_item_picks_latest_unfinished_and_suggestions_use_latest_opened() -> None:
    """US-NH-80 TC5: dẫn đúng trang đang đọc; gợi ý lấy chương vừa mở gần nhất."""
    older = _series(1, datetime(2026, 10, 20, tzinfo=timezone.utc))
    newer_done = _series(2, datetime(2026, 10, 24, tzinfo=timezone.utc), completed=True)
    use_case, terms = _use_case(_facts(), [older, newer_done], terms=["你好"])
    plan = await use_case.execute(USER)
    reading = next(i for i in plan.items if i.kind is TodayKind.CONTINUE_READING)
    assert (reading.action.chapter_id, reading.action.page_no) == (10, 2)
    suggestion = next(i for i in plan.items if i.kind is TodayKind.CHAPTER_SUGGESTIONS)
    assert suggestion.action.chapter_id == 20 and terms.chapters == [20]


async def test_nothing_to_do_returns_all_done_and_new_learner_gets_get_started() -> None:
    """US-NH-80 TC7 và ngoại lệ người mới."""
    done, _ = _use_case(_facts(due=0), [_series(1, NOW, completed=True)])
    plan = await done.execute(USER)
    assert plan.all_done and plan.items == [] and plan.message
    fresh, _ = _use_case(_facts(due=0, words=0, cards=0))
    started = await fresh.execute(USER)
    assert _kinds(started) == [TodayKind.GET_STARTED] and started.items[0].action.type == "library"
    assert not started.all_done


async def test_failing_source_drops_only_its_item() -> None:
    """Ngoại lệ F12.04: lỗi một nguồn chỉ làm mất thẻ việc đó."""
    use_case, _ = _use_case(RuntimeError("boom"), [_series(1, NOW)])
    assert _kinds(await use_case.execute(USER)) == [TodayKind.CONTINUE_READING]


async def test_items_are_capped_by_max_items() -> None:
    use_case, _ = _use_case(
        _facts(due=30),
        [_series(1, NOW)],
        WeakWords(12, 6),
        goal=10,
        terms=["你好"],
        rules=TodayRules(20, 5, 0.7, 2, 10),
    )
    assert len((await use_case.execute(USER)).items) == 2
