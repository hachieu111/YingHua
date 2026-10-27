from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from app.core.clock import Clock
from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.stats.application.dto import SystemStats
from app.modules.stats.application.ports import (
    ContentCountsSource,
    ImagingCountsSource,
    StatsUnitOfWork,
    UserCountsSource,
    VocabCountsSource,
)


class GetSystemStatsUseCase:
    """F12.03 — Thống kê toàn hệ thống cho quản trị viên (US-QT-08).

    Người dùng, truyện, trang theo trạng thái xử lý ảnh, tỉ lệ nhận diện thành công/thất bại, số từ đã lưu
    và số người học hoạt động theo ngày (UTC). Chỉ số liệu tổng hợp; hệ thống mới thì mọi số bằng 0.
    """

    def __init__(
        self,
        uow_factory: Callable[[], StatsUnitOfWork],
        users: UserCountsSource,
        content: ContentCountsSource,
        imaging: ImagingCountsSource,
        vocab: VocabCountsSource,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._users = users
        self._content = content
        self._imaging = imaging
        self._vocab = vocab
        self._clock = clock

    async def execute(self, identity: Identity) -> SystemStats:
        if not identity.is_admin:
            raise PermissionDeniedError()
        now = self._clock.now()
        today = now.date()
        imaging = await self._imaging.imaging_counts()
        finished = imaging.done + imaging.failed
        async with self._uow_factory() as uow:
            active_today = await uow.activity.system_totals(today, today)
            active_7 = await uow.activity.system_totals(today - timedelta(days=6), today)
            active_30 = await uow.activity.system_totals(today - timedelta(days=29), today)
        return SystemStats(
            generated_at=now,
            users=await self._users.user_counts(now),
            content=await self._content.content_counts(),
            imaging=imaging,
            ocr_success_rate=imaging.done / finished if finished > 0 else None,
            vocab=await self._vocab.vocab_counts(),
            active_today=active_today,
            active_7_days=active_7,
            active_30_days=active_30,
        )
