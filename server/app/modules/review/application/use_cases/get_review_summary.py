from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.review.application.dto import ReviewSummary
from app.modules.review.application.ports import ReviewUnitOfWork, UserTimezoneSource
from app.modules.review.domain.rules import local_day_bounds

DEFAULT_TIMEZONE_NAME = "UTC"


class GetReviewSummaryUseCase:
    """F08.07, F08.01 — Tổng kết phiên ôn: màn "hoàn thành" hay "chưa có thẻ" (US-NH-44).

    "Hôm nay" theo múi giờ của người học (M02), thiếu thì dùng UTC. `status`: `no_cards` (chưa có thẻ),
    `due` (còn thẻ đến hạn), `completed` (đã ôn xong, kèm hạn kế tiếp và số thẻ còn đến hạn trong ngày).
    Thêm `due_words` (số mục từ có thẻ đến hạn) và `status_counts` (số mục từ theo trạng thái) để đầu trang
    không phải tải cả danh sách. Quản trị viên xem của người khác qua `owner_id` (F13.07).
    """

    def __init__(
        self, uow_factory: Callable[[], ReviewUnitOfWork], timezones: UserTimezoneSource, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._timezones = timezones
        self._clock = clock

    async def execute(self, identity: Identity, owner_id: int | None = None) -> ReviewSummary:
        user_id = resolve_owner(identity, owner_id)
        now = self._clock.now()
        tz_name = await self._timezones.timezone_of(identity, user_id)
        day_start, day_end = local_day_bounds(now, tz_name)
        async with self._uow_factory() as uow:
            total_cards = await uow.cards.count_cards(user_id)
            reviewed_today = await uow.logs.count_between(user_id, day_start, day_end)
            due_now = await uow.cards.count_due(user_id, now, None, None)
            due_by_day_end = await uow.cards.count_due(user_id, day_end, None, None)
            next_due_at = await uow.cards.next_due_after(user_id, now)
            due_words = await uow.cards.count_due_words(user_id, now)
            status_counts = await uow.vocab.status_counts(user_id)
        if total_cards == 0:
            status = "no_cards"
        elif due_now > 0:
            status = "due"
        else:
            status = "completed"
        return ReviewSummary(
            status=status,
            reviewed_today=reviewed_today,
            due_now=due_now,
            due_later_today=max(0, due_by_day_end - due_now),
            next_due_at=next_due_at,
            total_cards=total_cards,
            timezone=tz_name or DEFAULT_TIMEZONE_NAME,
            due_words=due_words,
            status_counts=status_counts,
        )
