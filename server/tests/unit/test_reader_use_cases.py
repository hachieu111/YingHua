"""M05 — quy tắc ghi chú, bản sửa dịch và giới hạn tra từ của Khách: F05.04, F05.05, F05.08."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from app.core.errors import NotFoundError
from app.modules.auth.application.public import Identity, Role
from app.modules.imaging.domain.entities import Bubble
from app.modules.library.application.dto import PageAccess
from app.modules.reader.application.use_cases.lookup_bubble_word import LookupBubbleWordUseCase
from app.modules.reader.domain.entities import AnnotationInput, ConsumeOutcome, Stroke
from app.modules.reader.domain.errors import (
    AnnotationTooLargeError,
    BubbleNotFoundError,
    EditTooLongError,
    EmptyTranslationError,
    GuestLookupLimitReachedError,
    InvalidAnnotationError,
    WordNotInBubbleError,
)
from app.modules.reader.domain.rules import (
    MAX_ANNOTATION_BYTES,
    MAX_EDIT_CHARS,
    MAX_STROKES,
    MAX_TOTAL_STROKE_POINTS,
    clean_edit_text,
    contains_word,
    percent,
    validate_annotations,
)
from tests.conftest import FixedClock

NOW = datetime(2026, 10, 24, 8, 0, tzinfo=timezone.utc)


def _stroke(points: int = 3, color: str = "#aabbcc") -> Stroke:
    return Stroke(color, tuple((float(i), float(i)) for i in range(points)))


def test_clean_edit_text_trims_and_enforces_length() -> None:
    """US-NH-24: bản dịch 1..1000 ký tự, không trống."""
    assert clean_edit_text("  xin chào  ") == "xin chào"
    with pytest.raises(EmptyTranslationError):
        clean_edit_text("   \n ")
    with pytest.raises(EditTooLongError):
        clean_edit_text("a" * (MAX_EDIT_CHARS + 1))
    assert len(clean_edit_text("a" * MAX_EDIT_CHARS)) == MAX_EDIT_CHARS


def test_validate_annotations_accepts_valid_and_rejects_bad_color_or_coordinates() -> None:
    """US-NH-64: màu #rrggbb, tọa độ hữu hạn, nét có điểm."""
    validate_annotations(AnnotationInput({5: "#FF00aa"}, (_stroke(),)))
    validate_annotations(AnnotationInput())
    bad_inputs = [
        AnnotationInput({5: "red"}),
        AnnotationInput({5: "#fff"}),
        AnnotationInput(strokes=(_stroke(color="#12345g"),)),
        AnnotationInput(strokes=(Stroke("#aabbcc", ()),)),
        AnnotationInput(strokes=(Stroke("#aabbcc", ((float("nan"), 0.0),)),)),
        AnnotationInput(strokes=(Stroke("#aabbcc", ((1e9, 0.0),)),)),
    ]
    for bad in bad_inputs:
        with pytest.raises(InvalidAnnotationError):
            validate_annotations(bad)


def test_validate_annotations_enforces_stroke_point_and_size_limits() -> None:
    too_many_strokes = AnnotationInput(strokes=tuple(_stroke(1) for _ in range(MAX_STROKES + 1)))
    with pytest.raises(AnnotationTooLargeError):
        validate_annotations(too_many_strokes)
    chunk = MAX_TOTAL_STROKE_POINTS // 2 + 1
    with pytest.raises(AnnotationTooLargeError):
        validate_annotations(AnnotationInput(strokes=(_stroke(chunk), _stroke(chunk))))
    # Ít nét nhưng nhiều điểm lẻ → vượt 256 KB dù chưa chạm giới hạn số điểm.
    heavy = Stroke(
        "#aabbcc", tuple((123456.789012 + i, 654321.210987 + i) for i in range(MAX_ANNOTATION_BYTES // 30))
    )
    with pytest.raises(AnnotationTooLargeError):
        validate_annotations(AnnotationInput(strokes=(heavy,)))


def test_percent_and_contains_word() -> None:
    assert percent(25, 100) == 25.0 and percent(1, 3) == 33.3333
    assert percent(5, None) is None and percent(5, 0) is None
    assert contains_word("你好吗？", "你好") and contains_word("你好", " 你好 ")
    assert not contains_word("你好", "再见") and not contains_word("你好", "  ")


class FakeGuests:
    def __init__(self, limit_used: int = 0) -> None:
        self.sessions: dict[uuid.UUID, int] = {}
        self.created = 0
        self._preset = limit_used

    async def consume(self, session_id: uuid.UUID, limit: int, now: datetime) -> tuple[ConsumeOutcome, int]:
        used = self.sessions.get(session_id)
        if used is None:
            return ConsumeOutcome.UNKNOWN, 0
        if used >= limit:
            return ConsumeOutcome.LIMIT_REACHED, used
        self.sessions[session_id] = used + 1
        return ConsumeOutcome.OK, used + 1

    async def create(self, now: datetime, expires_at: datetime, used: int) -> uuid.UUID:
        session_id = uuid.uuid4()
        self.sessions[session_id] = used
        self.created += 1
        return session_id


class FakeBubbles:
    def __init__(self, bubble: Bubble | None) -> None:
        self._bubble = bubble

    async def get(self, bubble_id: int) -> Bubble | None:
        return self._bubble if self._bubble and self._bubble.id == bubble_id else None


class FakeUow:
    def __init__(self, bubble: Bubble | None) -> None:
        self.bubbles = FakeBubbles(bubble)
        self.guests = FakeGuests()

    async def __aenter__(self) -> FakeUow:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def commit(self) -> None:
        return None


class FakePages:
    def __init__(self, readable: bool = True) -> None:
        self.readable = readable

    async def can_read_translation(self, identity: Identity | None, translation_id: int) -> bool:
        return self.readable

    async def get_page(self, *args: Any, **kwargs: Any) -> PageAccess:  # pragma: no cover - không dùng
        raise NotImplementedError


class FakeDictionary:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Identity | None]] = []

    async def lookup(self, term: str, identity: Identity | None) -> Any:
        self.calls.append((term, identity))
        return object()


def _bubble() -> Bubble:
    return Bubble(
        id=1, translation_id=10, idx=0, class_name="speech_bubble", x=0, y=0, w=5, h=5, text_zh="你好吗"
    )


def _use_case(
    uow: FakeUow, pages: FakePages, dictionary: FakeDictionary, limit: int = 2
) -> LookupBubbleWordUseCase:
    return LookupBubbleWordUseCase(
        lambda: uow,  # type: ignore[arg-type,return-value]
        pages,  # type: ignore[arg-type]
        dictionary,  # type: ignore[arg-type]
        FixedClock(NOW),
        limit,
        timedelta(hours=24),
    )


async def test_guest_lookup_creates_session_counts_and_stops_at_limit() -> None:
    """US-KH-05: Khách tra tối đa N lượt mỗi phiên; hết lượt không trả kết quả."""
    uow, dictionary = FakeUow(_bubble()), FakeDictionary()
    use_case = _use_case(uow, FakePages(), dictionary, limit=2)
    first = await use_case.execute(None, None, 1, "你好")
    assert first.guest is not None and (first.guest.used, first.guest.remaining) == (1, 1)
    session = uuid.UUID(first.guest.session_id)
    second = await use_case.execute(None, session, 1, "你好")
    assert second.guest is not None and second.guest.remaining == 0
    with pytest.raises(GuestLookupLimitReachedError) as raised:
        await use_case.execute(None, session, 1, "你好")
    assert raised.value.details["login_required"] is True
    assert len(dictionary.calls) == 2  # lượt thứ ba không chạm tới từ điển
    # Phiên lạ (hoặc hết hạn) được cấp phiên mới với bộ đếm 1.
    fresh = await use_case.execute(None, uuid.uuid4(), 1, "你好")
    assert fresh.guest is not None and fresh.guest.used == 1 and uow.guests.created == 2


async def test_logged_in_lookup_is_not_limited_and_validates_bubble_and_word() -> None:
    uow, dictionary = FakeUow(_bubble()), FakeDictionary()
    use_case = _use_case(uow, FakePages(), dictionary, limit=1)
    user = Identity(user_id=3, role=Role.USER, session_id="s")
    for _ in range(3):
        result = await use_case.execute(user, None, 1, "你好")
        assert result.guest is None
    with pytest.raises(WordNotInBubbleError):
        await use_case.execute(user, None, 1, "再见")
    with pytest.raises(BubbleNotFoundError):
        await use_case.execute(user, None, 999, "你好")
    hidden = _use_case(uow, FakePages(readable=False), dictionary)
    with pytest.raises(NotFoundError):
        await hidden.execute(None, None, 1, "你好")
