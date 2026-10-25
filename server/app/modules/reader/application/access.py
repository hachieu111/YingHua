"""Kiểm quyền bong bóng dùng chung cho các use case của M05 (F03.10)."""

from __future__ import annotations

from app.modules.auth.application.public import Identity
from app.modules.imaging.application.public import Bubble
from app.modules.library.application.public import PageAccessPort
from app.modules.reader.application.ports import ReaderUnitOfWork
from app.modules.reader.domain.errors import BubbleNotFoundError


async def load_readable_bubble(
    uow: ReaderUnitOfWork, pages: PageAccessPort, identity: Identity | None, bubble_id: int
) -> Bubble:
    """Bong bóng thuộc bản dịch có ít nhất một trang người gọi được đọc; ngược lại trả như không tồn tại."""
    bubble = await uow.bubbles.get(bubble_id)
    if bubble is None or not await pages.can_read_translation(identity, bubble.translation_id):
        raise BubbleNotFoundError()
    return bubble
