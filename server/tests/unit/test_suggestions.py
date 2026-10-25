"""M10 — chấm điểm gợi ý, gom từ trong chương, use case với bản giả (US-NH-51, US-NH-52)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

import pytest

from app.core.common_chars import is_stop_term
from app.core.errors import NotFoundError
from app.modules.imaging.domain.entities import Bubble
from app.modules.suggestions.application.ports import ChapterPage, TermBrief
from app.modules.suggestions.application.use_cases.accept_suggestion import AcceptSuggestionUseCase
from app.modules.suggestions.application.use_cases.dismissals import (
    DismissSuggestionUseCase,
    ListDismissedUseCase,
    RestoreSuggestionUseCase,
)
from app.modules.suggestions.application.use_cases.list_suggestions import ListSuggestionsUseCase
from app.modules.suggestions.domain.entities import BubbleTokens, DismissedTerm, TermStats
from app.modules.suggestions.domain.errors import InvalidSuggestionTermError, SuggestionNotFoundError
from app.modules.suggestions.domain.rules import (
    collect_stats,
    fold_reduplication,
    hsk_fit,
    normalize_term,
    rank_terms,
    reduplication_root,
)
from app.modules.vocab.application.public import SaveWordCommand
from tests.conftest import FixedClock
from tests.unit.review_fakes import identity

NOW = datetime(2026, 10, 24, 8, 0, tzinfo=timezone.utc)


def _tokens(*words: str) -> list[dict[str, Any]]:
    return [{"word": w, "pinyin": f"py-{w}"} for w in words]


def test_collect_stats_counts_only_han_tokens_and_keeps_first_occurrence() -> None:
    bubbles = [
        BubbleTokens(10, 1, 100, 0, _tokens("你好", "，", "abc", "你好吗", "")),
        BubbleTokens(11, 2, 200, 0, [*_tokens("你好"), "xyz", {"word": 5}]),
    ]
    stats = collect_stats(bubbles)
    assert set(stats) == {"你好", "你好吗"}
    assert (stats["你好"].occurrences, stats["你好"].page_id, stats["你好"].bubble_id) == (2, 10, 100)
    assert stats["你好"].pinyin == "py-你好"


def test_hsk_fit_peaks_at_level_and_one_above_and_drops_for_known_words() -> None:
    assert hsk_fit(3, 3) == hsk_fit(4, 3) == 1.0
    assert hsk_fit(5, 3) < 1.0 and hsk_fit(7, 3) < hsk_fit(5, 3)
    assert hsk_fit(2, 3) < 1.0 and hsk_fit(1, 3) < hsk_fit(2, 3)
    assert hsk_fit(None, 3) < hsk_fit(5, 3)


def _stat(term: str, occurrences: int) -> TermStats:
    return TermStats(term, occurrences, 1, 1, 1)


def test_rank_terms_with_level_uses_hsk_fit_and_lookups() -> None:
    stats = {"甲": _stat("甲", 3), "乙": _stat("乙", 3), "丙": _stat("丙", 3), "丁": _stat("丁", 3)}
    levels: dict[str, int | None] = {"甲": 3, "乙": 1, "丙": 9, "丁": None}
    ranked = [t.stats.term for t in rank_terms(stats, {}, levels, 3)]
    assert ranked[0] == "甲" and ranked[-1] in {
        "乙",
        "丙",
    }  # đúng trình độ lên đầu, đã biết/quá khó xuống cuối
    boosted = rank_terms(stats, {"乙": 5}, levels, 3)
    assert next(t for t in boosted if t.stats.term == "乙").lookups == 5
    assert [t.stats.term for t in boosted].index("乙") < ranked.index("乙")  # tra nhiều thì được đẩy lên


def test_rank_terms_without_level_orders_by_frequency_then_lookups() -> None:
    stats = {"甲": _stat("甲", 1), "乙": _stat("乙", 5), "丙": _stat("丙", 5)}
    ranked = rank_terms(stats, {"甲": 4}, {"甲": 1, "乙": 9, "丙": 2}, None)
    assert [t.stats.term for t in ranked] == ["乙", "丙", "甲"]  # cấp HSK không ảnh hưởng khi chưa khai báo
    assert rank_terms({}, {}, {}, None) == []


def test_normalize_term_requires_pure_han() -> None:
    assert normalize_term(" 你好 ") == "你好"
    for bad in ("", "abc", "你好a", "你" * 33):
        with pytest.raises(InvalidSuggestionTermError):
            normalize_term(bad)


class FakeChapters:
    def __init__(self, pages: list[ChapterPage], missing: bool = False) -> None:
        self.pages = pages
        self.missing = missing

    async def pages_of(self, identity: Any, chapter_id: int) -> list[ChapterPage]:
        if self.missing:
            raise NotFoundError()
        return self.pages


class FakeBubbles:
    def __init__(self, by_translation: dict[int, list[Bubble]]) -> None:
        self.by_translation = by_translation

    async def list_by_translation(self, translation_id: int) -> list[Bubble]:
        return self.by_translation.get(translation_id, [])


class FakeDismissed:
    def __init__(self) -> None:
        self.rows: dict[str, datetime] = {}

    async def terms(self, user_id: int) -> set[str]:
        return set(self.rows)

    async def page(self, user_id: int, offset: int, limit: int) -> tuple[list[DismissedTerm], int]:
        rows = sorted(self.rows.items(), key=lambda kv: kv[1], reverse=True)
        return [DismissedTerm(t, at) for t, at in rows[offset : offset + limit]], len(rows)

    async def add(self, user_id: int, term: str, now: datetime) -> None:
        self.rows.setdefault(term, now)

    async def remove(self, user_id: int, term: str) -> None:
        self.rows.pop(term, None)


class FakeUow:
    def __init__(self, bubbles: dict[int, list[Bubble]], saved: set[str], lookups: dict[str, int]) -> None:
        self.bubbles = FakeBubbles(bubbles)
        self.dismissed = FakeDismissed()
        self._saved = saved
        self._lookups = lookups
        self.saved = self
        self.lookups = self

    async def saved_terms(self, user_id: int, terms: Sequence[str]) -> set[str]:
        return self._saved & set(terms)

    async def count_by_term(self, user_id: int, terms: Sequence[str]) -> dict[str, int]:
        return {t: n for t, n in self._lookups.items() if t in terms}

    async def __aenter__(self) -> FakeUow:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def commit(self) -> None:
        return None


class FakeHints:
    KNOWN = frozenset({"看", "学习", "你好", "朋友"})

    async def known_terms(self, terms: Sequence[str]) -> set[str]:
        return {t for t in terms if t in self.KNOWN}

    async def hsk_levels(self, terms: Sequence[str]) -> dict[str, int | None]:
        return {t: 3 for t in terms}

    async def briefs(self, terms: Sequence[str]) -> dict[str, TermBrief]:
        return {t: TermBrief("py", "[x] ① nghĩa của " + t + " ② khác") for t in terms}


class FakeLevel:
    def __init__(self, level: int | None) -> None:
        self.level = level

    async def hsk_level_of(self, user_id: int) -> int | None:
        return self.level


def _bubble(bubble_id: int, translation_id: int, idx: int, *words: str) -> Bubble:
    return Bubble(
        bubble_id, translation_id, idx, "speech_bubble", 0, 0, 1, 1, "".join(words), tokens=_tokens(*words)
    )


def _setup(saved: set[str] | None = None) -> tuple[FakeUow, FakeChapters]:
    bubbles = {
        1: [_bubble(11, 1, 0, "你好", "学习"), _bubble(12, 1, 1, "学习", "朋友")],
        2: [_bubble(21, 2, 0, "朋友", "学习")],
    }
    pages = [
        ChapterPage(101, 1, 1, "done"),
        ChapterPage(102, 2, 2, "done"),
        ChapterPage(103, 3, 3, "running"),
        ChapterPage(104, 4, 4, "failed"),
    ]
    return FakeUow(bubbles, saved or set(), {"朋友": 3}), FakeChapters(pages)


def _list_use_case(uow: FakeUow, chapters: FakeChapters, level: int | None = 3) -> ListSuggestionsUseCase:
    return ListSuggestionsUseCase(lambda: uow, chapters, FakeHints(), FakeLevel(level))


async def test_list_suggestions_counts_excludes_saved_and_dismissed_and_reports_processing() -> None:
    uow, chapters = _setup(saved={"你好"})
    await uow.dismissed.add(1, "朋友", NOW)
    result = await _list_use_case(uow, chapters).execute(identity(1), 7, 20)
    assert result.status == "processing"  # còn trang running; trang failed không giữ trạng thái này
    assert result.hsk_level == 3
    assert [s.term for s in result.items] == ["学习"]
    item = result.items[0]
    assert (item.occurrences, item.bubble_id, item.page_id, item.page_no) == (3, 11, 101, 1)
    assert item.meaning_vi == "nghĩa của 学习"  # nghĩa ngắn
    assert item.pinyin == "py-学习"


async def test_list_suggestions_ready_when_all_done_and_uses_lookup_history() -> None:
    uow, chapters = _setup()
    chapters.pages = chapters.pages[:2]
    result = await _list_use_case(uow, chapters, level=None).execute(identity(1), 7, 2)
    assert result.status == "ready" and result.hsk_level is None
    assert len(result.items) == 2 and {"学习", "朋友"} == {s.term for s in result.items}
    assert next(s for s in result.items if s.term == "朋友").lookups == 3


async def test_list_suggestions_unreadable_chapter_is_not_found() -> None:
    uow, chapters = _setup()
    chapters.missing = True
    with pytest.raises(NotFoundError):
        await _list_use_case(uow, chapters).execute(identity(1), 7, 20)


class FakeSaver:
    def __init__(self) -> None:
        self.commands: list[SaveWordCommand] = []

    async def execute(self, identity: Any, command: SaveWordCommand) -> Any:
        self.commands.append(command)
        return "saved"


async def test_accept_saves_first_occurrence_with_suggestion_origin() -> None:
    """US-NH-52 TC1/TC3: lưu như thao tác thường, lấy bong bóng đầu tiên làm ngữ cảnh."""
    uow, chapters = _setup(saved={"学习"})  # đã có trong sổ tay vẫn được chuyển cho F07.02 xử lý
    saver = FakeSaver()
    result = await AcceptSuggestionUseCase(lambda: uow, chapters, saver, FakeHints()).execute(
        identity(1), 7, " 学习 "
    )
    assert result == "saved"
    assert saver.commands == [SaveWordCommand("学习", "suggestion", 11, 101)]
    with pytest.raises(SuggestionNotFoundError):
        await AcceptSuggestionUseCase(lambda: uow, chapters, saver, FakeHints()).execute(
            identity(1), 7, "不存在"
        )
    with pytest.raises(InvalidSuggestionTermError):
        await AcceptSuggestionUseCase(lambda: uow, chapters, saver, FakeHints()).execute(
            identity(1), 7, "abc"
        )


async def test_dismiss_is_idempotent_listed_and_restorable() -> None:
    """US-NH-52 TC2/TC4: bỏ qua, xem mục Đã bỏ qua, khôi phục (kể cả khi không có)."""
    uow, _ = _setup()
    clock = FixedClock(NOW)
    me = identity(1)
    await DismissSuggestionUseCase(lambda: uow, clock).execute(me, "学习")
    await DismissSuggestionUseCase(lambda: uow, clock).execute(me, "学习")
    page = await ListDismissedUseCase(lambda: uow, FakeHints()).execute(me, 1, 20)
    assert page.total == 1 and page.items[0].dismissed.term == "学习"
    assert page.items[0].meaning_vi == "nghĩa của 学习" and page.items[0].hsk_level == 3
    restore = RestoreSuggestionUseCase(lambda: uow)
    await restore.execute(me, "学习")
    await restore.execute(me, "学习")
    assert (await ListDismissedUseCase(lambda: uow, FakeHints()).execute(me, 1, 20)).total == 0


def test_stop_terms_are_function_words_or_made_of_very_common_chars() -> None:
    """F10.01: 是, 什么, 我们 là từ quá cơ bản nên không gợi ý; 学习 thì có."""
    assert all(is_stop_term(t) for t in ("是", "什么", "我们", "没有", "不是"))
    assert not any(is_stop_term(t) for t in ("学习", "朋友", "看看"))


def test_reduplication_root_and_folding_need_root_in_dictionary() -> None:
    assert reduplication_root("看看") == "看" and reduplication_root("学习学习") == "学习"
    assert reduplication_root("看") is None and reduplication_root("学习朋友") is None
    stats = {
        "看看": _stat("看看", 2),
        "看": _stat("看", 3),
        "试试": _stat("试试", 4),
        "学习学习": _stat("学习学习", 1),
    }
    folded = fold_reduplication(stats, {"看", "学习"})
    assert folded["看"].occurrences == 5  # 看看 gộp vào 看 dù xuất hiện trước
    assert "看看" not in folded and "学习学习" not in folded
    assert folded["学习"].occurrences == 1 and folded["学习"].pinyin is None
    assert "试试" in folded  # từ gốc 试 không có trong từ điển: giữ nguyên


def test_rank_terms_without_level_lowers_hsk1_words() -> None:
    stats = {"甲": _stat("甲", 5), "乙": _stat("乙", 4)}
    ranked = rank_terms(stats, {}, {"甲": 1, "乙": 4}, None)
    assert [t.stats.term for t in ranked] == ["乙", "甲"]  # 甲 nhiều hơn nhưng là HSK 1
    with_level = rank_terms(stats, {}, {"甲": 1, "乙": 4}, 4)
    assert with_level[0].stats.term == "乙"


async def test_list_suggestions_drops_stop_terms_and_folds_reduplication() -> None:
    bubbles = {1: [_bubble(11, 1, 0, "什么", "看看", "看", "学习")]}
    uow = FakeUow(bubbles, set(), {})
    chapters = FakeChapters([ChapterPage(101, 1, 1, "done")])
    result = await _list_use_case(uow, chapters, level=None).execute(identity(1), 7, 20)
    terms = {s.term: s for s in result.items}
    assert set(terms) == {"看", "学习"}  # 什么 bị loại, 看看 gộp vào 看
    assert terms["看"].occurrences == 2
