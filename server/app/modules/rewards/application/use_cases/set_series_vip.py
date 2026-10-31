from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.rewards.application.dto import SeriesVipResult
from app.modules.rewards.application.ports import RewardsUnitOfWork
from app.modules.rewards.domain.errors import SeriesNotPublicError, VipSeriesNotFoundError


class SetSeriesVipUseCase:
    """F17.09 - Đặt hoặc bỏ cờ VIP cho truyện công khai (US-QT-17).

    Truyện riêng tư không có khái niệm VIP (409 `SERIES_NOT_PUBLIC`). Truyện chưa có chương đọc thử vẫn lưu
    được nhưng trả cảnh báo. Ghi nhật ký quản trị `series.vip_changed` trong cùng giao dịch (F13.06).
    """

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, actor: Identity, series_id: int, is_vip: bool) -> SeriesVipResult:
        if not actor.is_admin:
            raise PermissionDeniedError()
        async with self._uow_factory() as uow:
            series = await uow.series.get(series_id)
            if series is None:
                raise VipSeriesNotFoundError()
            if is_vip and not series.is_public:
                raise SeriesNotPublicError()
            if series.is_vip != is_vip:
                await uow.series.set_vip(series_id, is_vip)
                await uow.audit.add(
                    actor.user_id,
                    "series.vip_changed",
                    "series",
                    series_id,
                    {"from": series.is_vip, "to": is_vip},
                    self._clock.now(),
                )
            has_trial = await uow.series.has_trial_chapter(series_id)
            await uow.commit()
        return SeriesVipResult(series_id, is_vip, has_trial)
