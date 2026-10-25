from __future__ import annotations

from collections.abc import Callable

from app.core.errors import PermissionDeniedError
from app.modules.auth.application.public import Identity
from app.modules.imaging.application.dto import TranslationList
from app.modules.imaging.application.ports import ImagingUnitOfWork
from app.modules.imaging.domain.entities import TranslationStatus


class ListTranslationsUseCase:
    """F04.05 — Quản trị viên giám sát hàng đợi xử lý ảnh (US-QT-06).

    Trả danh sách (lọc theo trạng thái, phân trang), số việc theo từng trạng thái và thời gian xử lý trung
    bình. Lý do lỗi do pipeline ghi (bước + thông điệp) nằm trong từng dòng `failed`.
    """

    def __init__(self, uow_factory: Callable[[], ImagingUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(
        self, admin: Identity, status: TranslationStatus | None, page: int, size: int
    ) -> TranslationList:
        if not admin.is_admin:
            raise PermissionDeniedError()
        async with self._uow_factory() as uow:
            items, total = await uow.translations.list_page(status, (page - 1) * size, size)
            stats = await uow.translations.stats()
        return TranslationList(items=items, total=total, stats=stats)
