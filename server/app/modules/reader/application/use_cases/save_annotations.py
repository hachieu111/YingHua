from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.admin.application.public import record_admin_action, resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.reader.application.ports import ReaderUnitOfWork
from app.modules.reader.domain.entities import Annotation, AnnotationInput
from app.modules.reader.domain.rules import validate_annotations


class SaveAnnotationsUseCase:
    """F05.08 — Lưu ghi chú trên trang: tô màu bong bóng và nét vẽ tự do (US-NH-64).

    Thay toàn bộ ghi chú cũ của trang; giới hạn số nét, số điểm, dung lượng (rules.py). Chỉ người dùng
    đang đăng nhập và có quyền đọc trang; dữ liệu theo `user_id`.
    Quản trị viên sửa của người khác qua `owner_id`, ghi nhật ký `user_data.annotation.update` (F13.07).
    """

    def __init__(
        self, uow_factory: Callable[[], ReaderUnitOfWork], pages: PageAccessPort, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._clock = clock

    async def execute(
        self, identity: Identity, page_id: int, data: AnnotationInput, owner_id: int | None = None
    ) -> Annotation:
        owner = resolve_owner(identity, owner_id)
        now = self._clock.now()
        validate_annotations(data)
        await self._pages.get_page(identity, page_id)
        async with self._uow_factory() as uow:
            annotation = await uow.annotations.save(owner, page_id, data, now)
            await record_admin_action(
                uow.audit, identity, owner, "user_data.annotation.update", "page_annotation", page_id, now
            )
            await uow.commit()
        return annotation
