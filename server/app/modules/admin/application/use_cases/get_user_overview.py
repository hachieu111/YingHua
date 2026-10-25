from __future__ import annotations

from app.modules.admin.application.dto import UserOverview
from app.modules.admin.application.ports import UserActivitySource
from app.modules.admin.application.use_cases.ensure_target_user import EnsureTargetUserUseCase
from app.modules.auth.application.public import Identity


class GetUserOverviewUseCase:
    """F13.07 (US-QT-14) — Tổng quan một người dùng: hồ sơ cơ bản và số liệu học tập/nội dung.

    Hồ sơ không có mật khẩu băm hay token. Số liệu do `UserActivitySource` gom từ các module sở hữu dữ liệu.
    """

    def __init__(self, ensure_target: EnsureTargetUserUseCase, activity: UserActivitySource) -> None:
        self._ensure_target = ensure_target
        self._activity = activity

    async def execute(self, actor: Identity, target_user_id: int) -> UserOverview:
        user = await self._ensure_target.execute(actor, target_user_id)
        return UserOverview(user, await self._activity.collect(actor, target_user_id))
