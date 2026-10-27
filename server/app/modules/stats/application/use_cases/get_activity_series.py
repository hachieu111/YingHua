from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from app.core.clock import Clock
from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.stats.application.dto import ActivityReport
from app.modules.stats.application.ports import StatsUnitOfWork, UserTimezoneSource
from app.modules.stats.domain.activity import local_date
from app.modules.stats.domain.periods import (
    COMPARISON_DAYS,
    check_count,
    difference,
    parse_granularity,
    period_ranges,
    sum_period,
)


class GetActivitySeriesUseCase:
    """F12.01 — Biểu đồ hoạt động theo ngày/tuần/tháng kèm so sánh với tuần trước (US-NH-56).

    Mỗi mốc gồm số từ đã lưu, lượt ôn, trang đã đọc, bài kiểm tra và thời gian học. "Hôm nay" theo múi giờ
    người học. So sánh luôn là 7 ngày gần nhất so với 7 ngày liền trước đó (không phụ thuộc đơn vị biểu đồ,
    để thứ Hai không bị so với một tuần trống). Quản trị viên xem của người khác qua `owner_id` (F13.07).
    """

    def __init__(
        self, uow_factory: Callable[[], StatsUnitOfWork], timezones: UserTimezoneSource, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._timezones = timezones
        self._clock = clock

    async def execute(
        self, identity: Identity, granularity: str, count: int, owner_id: int | None = None
    ) -> ActivityReport:
        gran = parse_granularity(granularity)
        check_count(gran, count)
        user_id = resolve_owner(identity, owner_id)
        tz_name = await self._timezones.timezone_of(identity, user_id)
        today = local_date(self._clock.now(), tz_name)
        ranges = period_ranges(gran, today, count)
        current_start = today - timedelta(days=COMPARISON_DAYS - 1)
        previous_start = current_start - timedelta(days=COMPARISON_DAYS)
        start = min(ranges[0][0], previous_start)
        end = max(ranges[-1][1], today)
        async with self._uow_factory() as uow:
            days = await uow.activity.between(user_id, start, end)
        points = [sum_period(days, s, e) for s, e in ranges]
        current = sum_period(days, current_start, today)
        previous = sum_period(days, previous_start, current_start - timedelta(days=1))
        return ActivityReport(gran, tz_name, points, current, previous, difference(current, previous))
