from __future__ import annotations

from collections.abc import Callable, Sequence

from app.core.clock import Clock
from app.modules.rewards.application.ports import Decoration, RewardsUnitOfWork


class GetDecorationsUseCase:
    """F17.08 - Khung đang hiệu lực và dấu VIP của nhiều người bằng một truy vấn (cho bảng xếp hạng F16.07).

    Khung tạm hết hạn hoặc khung VIP khi hết VIP tự không hiện. Việc ẩn danh trên bảng xếp hạng (F16.08)
    do M16 quyết định bằng cách không dùng kết quả này cho người đã ẩn.
    """

    def __init__(self, uow_factory: Callable[[], RewardsUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, user_ids: Sequence[int]) -> dict[int, Decoration]:
        if not user_ids:
            return {}
        async with self._uow_factory() as uow:
            return await uow.wallets.decorations(user_ids, self._clock.now())
