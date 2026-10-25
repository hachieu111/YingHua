"""Quy tắc thuần của M08: đánh giá, bộ thẻ, ngày theo múi giờ người học, cập nhật thẻ sau lượt chấm."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.modules.review.domain.entities import (
    Card,
    CardState,
    CardType,
    DeckKind,
    DeckRef,
    NewCard,
    Rating,
    SchedulingState,
)
from app.modules.review.domain.errors import InvalidDeckError, InvalidRatingError

_SERIES_PREFIX = "series:"


def parse_rating(value: object) -> Rating:
    """Đúng bốn mức 1..4; bool và số thực bị từ chối."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidRatingError()
    try:
        return Rating(value)
    except ValueError as exc:
        raise InvalidRatingError() from exc


def parse_deck(value: str | None) -> DeckRef:
    """`None`/`all` → mọi thẻ; `starred`; `series:<id>`."""
    if value is None or value in ("", DeckKind.ALL.value):
        return DeckRef(DeckKind.ALL)
    if value == DeckKind.STARRED.value:
        return DeckRef(DeckKind.STARRED)
    if value.startswith(_SERIES_PREFIX):
        raw = value[len(_SERIES_PREFIX) :]
        if raw.isdigit() and 0 < int(raw) < 2**62:
            return DeckRef(DeckKind.SERIES, int(raw))
    raise InvalidDeckError()


def resolve_timezone(name: str | None) -> timezone | ZoneInfo:
    """Múi giờ người học; tên sai hoặc thiếu → UTC (F08.01: "hôm nay" theo múi giờ của người học)."""
    if not name:
        return timezone.utc
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return timezone.utc


def local_day_bounds(now: datetime, tz_name: str | None) -> tuple[datetime, datetime]:
    """[đầu, cuối) của ngày hiện tại theo múi giờ người học, đổi sang UTC."""
    tz = resolve_timezone(tz_name)
    local = now.astimezone(tz)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    # Cộng một ngày trên giờ địa phương rồi đổi sang UTC để đúng cả ngày chuyển giờ mùa hè.
    end = (start.replace(tzinfo=None) + timedelta(days=1)).replace(tzinfo=tz)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def new_cards(user_id: int, vocab_entry_id: int, initial: SchedulingState, now: datetime) -> list[NewCard]:
    """Ba thẻ nhận diện/nhớ lại/nghe ở trạng thái FSRS mới, đến hạn ngay lúc lưu (F08.09)."""
    return [NewCard(user_id, vocab_entry_id, t, initial, now) for t in CardType]


def is_lapse(state_before: CardState, rating: Rating) -> bool:
    """Quên một thẻ đã thuộc (đang ở trạng thái ôn) mới tính là một lần sai (lapse) theo FSRS."""
    return state_before is CardState.REVIEW and rating is Rating.AGAIN


def apply_review(card: Card, new_schedule: SchedulingState, rating: Rating, now: datetime) -> None:
    """Cập nhật thẻ sau một lượt chấm (S, D, hạn ôn, số lượt, số lần quên)."""
    if is_lapse(card.schedule.state, rating):
        card.lapses += 1
    card.reps += 1
    card.schedule = new_schedule
    card.updated_at = now


def reset_card(card: Card, initial: SchedulingState, now: datetime) -> None:
    """Đưa thẻ về như thẻ mới; giữ lịch sử ôn nên chỉ đổi trạng thái lập lịch (F08.05)."""
    card.schedule = initial
    card.reps = 0
    card.lapses = 0
    card.updated_at = now
