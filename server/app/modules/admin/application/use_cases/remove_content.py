from __future__ import annotations

import logging
from collections.abc import Callable

from app.core.clock import Clock
from app.core.errors import PermissionDeniedError
from app.modules.admin.application.dto import RemovalItem
from app.modules.admin.application.ports import AdminUnitOfWork, ContentOwnerNotifier
from app.modules.admin.domain.errors import (
    AlreadyRemovedError,
    RemovalTargetInvalidError,
    RemovalTargetNotFoundError,
)
from app.modules.admin.domain.moderation import clean_removal_reason
from app.modules.auth.application.public import Identity

logger = logging.getLogger(__name__)


class RemoveContentUseCase:
    """F13.04, F13.06 — Gỡ ảnh/trang vi phạm kèm lý do (US-QT-12 TC2–TC4).

    Đánh dấu ảnh gốc, ảnh dẫn xuất và ảnh ngữ cảnh cắt từ ảnh đó là "đã gỡ" (không còn phục vụ cho ai);
    từ và thẻ đã lưu vẫn còn. Ghi `content_removals` và nhật ký quản trị trong cùng giao dịch.

    Sau khi giao dịch đã commit, báo cho người tải ảnh (F14.05) bằng thông báo trong ứng dụng kèm lý do. Đây
    là giao dịch riêng của M14: thông báo lỗi chỉ ghi log, KHÔNG làm hỏng việc gỡ đã xong (gỡ ảnh vi phạm là
    việc chính, thông báo là hệ quả). Không báo khi không rõ chủ ảnh hoặc quản trị viên tự gỡ ảnh của mình.
    """

    def __init__(
        self, uow_factory: Callable[[], AdminUnitOfWork], clock: Clock, notifier: ContentOwnerNotifier
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._notifier = notifier

    async def execute(
        self, actor: Identity, page_id: int | None, file_id: int | None, reason: str | None
    ) -> RemovalItem:
        if not actor.is_admin:
            raise PermissionDeniedError()
        if (page_id is None) == (file_id is None):
            raise RemovalTargetInvalidError()
        clean_reason = clean_removal_reason(reason)
        now = self._clock.now()
        async with self._uow_factory() as uow:
            target = await uow.moderation.resolve_target(page_id, file_id)
            if target is None:
                raise RemovalTargetNotFoundError()
            removed = await uow.moderation.mark_removed(target.file_ids, now)
            if not removed:
                raise AlreadyRemovedError()
            removal_id = await uow.moderation.add_removal(
                target.root_file_id, target.page_id, clean_reason, actor.user_id, now
            )
            await uow.audit.add(
                actor.user_id,
                "content.removed",
                "page" if target.page_id is not None else "file",
                target.page_id if target.page_id is not None else target.root_file_id,
                {"reason": clean_reason, "file_count": len(removed), "owner_id": target.owner_id},
                now,
            )
            item = await uow.moderation.get_removal(removal_id)
            await uow.commit()
        await self._notify_owner(actor, target.owner_id, target.page_id, clean_reason)
        return item

    async def _notify_owner(
        self, actor: Identity, owner_id: int | None, page_id: int | None, reason: str
    ) -> None:
        if owner_id is None or owner_id == actor.user_id:
            return
        try:
            await self._notifier.content_removed(owner_id, page_id, reason)
        except Exception:
            logger.exception("Không gửi được thông báo gỡ ảnh cho người dùng %s", owner_id)
