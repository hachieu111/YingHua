from __future__ import annotations

from collections.abc import Callable

from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.stats.application.dto import LearningOverview
from app.modules.stats.application.ports import LearningFactsSource, StatsUnitOfWork, UserTimezoneSource


class GetLearningOverviewUseCase:
    """F12.01 — Thống kê học tập cá nhân: số từ, thẻ đến hạn, tỉ lệ nhớ (US-NH-56).

    Số liệu tính tại thời điểm xem (lưu thêm một từ thì số từ tăng đúng một). Tỉ lệ nhớ = số lượt ôn không
    chọn "Quên" / tổng lượt ôn; chưa có lượt ôn thì `retention_rate = None` (không chia cho 0, giao diện hiện
    "Chưa có dữ liệu"). Chỉ dữ liệu của chính người dùng; quản trị viên xem của người khác qua `owner_id`
    (F13.07).
    """

    def __init__(
        self,
        uow_factory: Callable[[], StatsUnitOfWork],
        facts: LearningFactsSource,
        timezones: UserTimezoneSource,
    ) -> None:
        self._uow_factory = uow_factory
        self._facts = facts
        self._timezones = timezones

    async def execute(self, identity: Identity, owner_id: int | None = None) -> LearningOverview:
        user_id = resolve_owner(identity, owner_id)
        facts = await self._facts.facts(identity, user_id)
        tz_name = await self._timezones.timezone_of(identity, user_id)
        async with self._uow_factory() as uow:
            totals = await uow.activity.lifetime_totals(user_id)
        retention = facts.reviews_recalled / facts.reviews_total if facts.reviews_total > 0 else None
        return LearningOverview(
            facts=facts,
            retention_rate=retention,
            pages_read_total=totals.pages_read,
            study_seconds_total=totals.study_seconds,
            timezone=tz_name,
        )
