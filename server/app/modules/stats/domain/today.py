"""Luật chọn và sắp xếp các việc "Hôm nay nên học gì" (F12.04, US-NH-80).

Thuần Python: thứ tự và điều kiện xuất hiện do luật cố định quyết định; câu nhắc sinh theo mẫu.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum


class TodayKind(str, Enum):
    """Thứ tự khai báo cũng là thứ tự hiển thị cố định (a) -> (e); GET_STARTED chỉ cho người mới."""

    REVIEW_DUE = "review_due"
    CONTINUE_READING = "continue_reading"
    TAKE_QUIZ = "take_quiz"
    WEEKLY_GOAL = "weekly_goal"
    CHAPTER_SUGGESTIONS = "chapter_suggestions"
    GET_STARTED = "get_started"


@dataclass(frozen=True, slots=True)
class TodayRules:
    """Các ngưỡng, lấy từ Settings ở tầng lắp ghép."""

    due_priority_threshold: int
    quiz_low_words: int
    quiz_low_retrievability: float
    max_items: int
    quiz_min_words: int


@dataclass(frozen=True, slots=True)
class TodayAction:
    """Đích điều hướng dạng dữ liệu; giao diện tự ánh xạ sang màn hình."""

    type: str  # review | reader | quiz | library | chapter_suggestions
    deck: str | None = None
    series_id: int | None = None
    chapter_id: int | None = None
    page_no: int | None = None


@dataclass(frozen=True, slots=True)
class TodayItem:
    kind: TodayKind
    title: str
    message: str
    action: TodayAction
    count: int | None = None
    urgent: bool = False
    priority: int = 0  # 1 = đứng đầu; gán khi sắp xếp


@dataclass(frozen=True, slots=True)
class ResumePoint:
    """Chương đang đọc dở (từ F03.12)."""

    series_id: int
    series_title: str
    chapter_id: int
    page_no: int | None


def review_due_item(cards_due: int, rules: TodayRules) -> TodayItem | None:
    if cards_due <= 0:
        return None
    urgent = cards_due >= rules.due_priority_threshold
    tail = " Ôn ngay để không bị quên nhé!" if urgent else ""
    return TodayItem(
        TodayKind.REVIEW_DUE,
        "Ôn thẻ đến hạn",
        f"Bạn có {cards_due} thẻ đến hạn hôm nay.{tail}",
        TodayAction("review", deck="all"),
        count=cards_due,
        urgent=urgent,
    )


def continue_reading_item(resume: ResumePoint | None) -> TodayItem | None:
    if resume is None:
        return None
    return TodayItem(
        TodayKind.CONTINUE_READING,
        "Đọc tiếp",
        f'Tiếp tục đọc "{resume.series_title}" từ chỗ bạn đang dừng.',
        TodayAction(
            "reader", series_id=resume.series_id, chapter_id=resume.chapter_id, page_no=resume.page_no
        ),
    )


def quiz_item(eligible_words: int, low_words: int, rules: TodayRules) -> TodayItem | None:
    """Chỉ khi sổ tay đủ điều kiện ra đề (F09.01) và có đủ từ độ nhớ thấp."""
    if eligible_words < rules.quiz_min_words or low_words < rules.quiz_low_words:
        return None
    return TodayItem(
        TodayKind.TAKE_QUIZ,
        "Làm bài kiểm tra",
        f"Có {low_words} từ bạn sắp quên. Làm một bài kiểm tra ngắn để nhớ lâu hơn nhé!",
        TodayAction("quiz"),
        count=low_words,
    )


def weekly_goal_item(goal: int | None, pages_this_week: int, resume: ResumePoint | None) -> TodayItem | None:
    if goal is None or goal <= 0 or pages_this_week >= goal:
        return None
    remaining = goal - pages_this_week
    action = (
        TodayAction(
            "reader", series_id=resume.series_id, chapter_id=resume.chapter_id, page_no=resume.page_no
        )
        if resume
        else TodayAction("library")
    )
    return TodayItem(
        TodayKind.WEEKLY_GOAL,
        "Mục tiêu tuần này",
        f"Bạn còn thiếu {remaining} trang để đạt mục tiêu tuần ({pages_this_week}/{goal} trang).",
        action,
        count=remaining,
    )


def suggestions_item(chapter_id: int, terms: Sequence[str]) -> TodayItem | None:
    if not terms:
        return None
    preview = ", ".join(terms[:3])
    return TodayItem(
        TodayKind.CHAPTER_SUGGESTIONS,
        "Từ nên học trong chương gần nhất",
        f"Chương bạn vừa đọc có {len(terms)} từ đáng học, như {preview}.",
        TodayAction("chapter_suggestions", chapter_id=chapter_id),
        count=len(terms),
    )


def get_started_item() -> TodayItem:
    """Người mới chưa có dữ liệu: gợi ý bắt đầu thay vì hiện số 0."""
    return TodayItem(
        TodayKind.GET_STARTED,
        "Bắt đầu hành trình",
        "Hãy mở một truyện trong Thư viện và đọc thử vài trang đầu tiên nhé!",
        TodayAction("library"),
    )


def arrange_items(items: Sequence[TodayItem | None], max_items: int) -> list[TodayItem]:
    """Bỏ việc không áp dụng, giữ thứ tự cố định theo `TodayKind`, cắt theo `max_items`, gán `priority`."""
    order = {kind: n for n, kind in enumerate(TodayKind)}
    present = sorted((i for i in items if i is not None), key=lambda i: order[i.kind])
    return [
        TodayItem(i.kind, i.title, i.message, i.action, i.count, i.urgent, rank)
        for rank, i in enumerate(present[:max_items], start=1)
    ]
