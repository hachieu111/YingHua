from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from app.core.clock import Clock
from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.stats.application.dto import StreakReport, StudyDay
from app.modules.stats.application.ports import ReadingProgressSource, StatsUnitOfWork, UserTimezoneSource
from app.modules.stats.domain.activity import local_date
from app.modules.stats.domain.streak import STREAK_RULE_TEXT, compute_streak

CALENDAR_DAYS = 7
READING_SERIES_LIMIT = 20


class GetStreakUseCase:
    """F12.02 — Chuỗi ngày học, lịch 7 ngày gần nhất và tiến độ đọc từng truyện (US-NH-57).

    Ngày có học = có ít nhất một lượt ôn hoặc một trang đọc mới, theo múi giờ người học (mỗi ngày tính một
    lần). Hôm nay chưa học thì chuỗi vẫn giữ tới hết ngày. Người mới: chuỗi 0, tiến độ đọc rỗng.
    Quản trị viên xem của người khác qua `owner_id` (F13.07).
    """

    def __init__(
        self,
        uow_factory: Callable[[], StatsUnitOfWork],
        timezones: UserTimezoneSource,
        reading: ReadingProgressSource,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._timezones = timezones
        self._reading = reading
        self._clock = clock

    async def execute(self, identity: Identity, owner_id: int | None = None) -> StreakReport:
        user_id = resolve_owner(identity, owner_id)
        tz_name = await self._timezones.timezone_of(identity, user_id)
        today = local_date(self._clock.now(), tz_name)
        week_start = today - timedelta(days=CALENDAR_DAYS - 1)
        async with self._uow_factory() as uow:
            study_days = await uow.activity.study_days(user_id)
            recent = {d.day: d for d in await uow.activity.between(user_id, week_start, today)}
        week = []
        for offset in range(CALENDAR_DAYS):
            day = week_start + timedelta(days=offset)
            row = recent.get(day)
            week.append(
                StudyDay(
                    day,
                    row.is_study_day if row else False,
                    row.reviews_count if row else 0,
                    row.pages_read if row else 0,
                )
            )
        reading = await self._reading.series_progress(user_id, READING_SERIES_LIMIT)
        return StreakReport(compute_streak(study_days, today), week, list(reading), tz_name, STREAK_RULE_TEXT)
