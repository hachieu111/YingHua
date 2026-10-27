from __future__ import annotations

from collections.abc import Callable

from app.core.errors import PermissionDeniedError
from app.modules.admin.application.dto import SamplePageCandidate
from app.modules.admin.application.ports import AdminUnitOfWork
from app.modules.auth.application.public import Identity

MAX_SAMPLE_PAGE_CANDIDATES = 100  # đủ cho ô chọn; trang mẫu chỉ cần một trang tiêu biểu


class ListSamplePageCandidatesUseCase:
    """F13.05, F04.16 — Liệt kê trang chọn được làm trang mẫu (US-QT-13 TC13).

    Chỉ các trang thuộc truyện công khai, đã dịch xong và ảnh chưa bị gỡ — cùng điều kiện mà
    `PATCH /admin/system-settings` kiểm khi lưu `sample_page_id`, nên mọi lựa chọn đều lưu được.
    """

    def __init__(self, uow_factory: Callable[[], AdminUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Identity) -> list[SamplePageCandidate]:
        if not actor.is_admin:
            raise PermissionDeniedError()
        async with self._uow_factory() as uow:
            return await uow.system_settings.list_sample_page_candidates(MAX_SAMPLE_PAGE_CANDIDATES)
