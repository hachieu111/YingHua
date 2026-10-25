from __future__ import annotations

from collections.abc import Callable

from app.core.storage import FileStorage
from app.modules.auth.application.public import Identity
from app.modules.imaging.application.dto import DownloadedImage
from app.modules.imaging.application.ports import ImagingUnitOfWork
from app.modules.imaging.domain.entities import ImageVariant, TranslationStatus
from app.modules.imaging.domain.errors import ImageFileNotFoundError, ImageNotReadyError
from app.modules.imaging.domain.rules import download_filename, variant_file_id
from app.modules.library.application.public import PageAccessPort


class DownloadPageImageUseCase:
    """F04.04 — Tải ảnh gốc / đã xóa chữ / đã dịch của một trang về máy (US-NH-20).

    Kiểm quyền đọc trang (F03.10) và ảnh chưa bị gỡ (F13.04). Hai dạng dẫn xuất chỉ tải được khi trang
    `done`. Tên tệp gợi ý theo truyện–chương–trang.
    """

    def __init__(
        self, uow_factory: Callable[[], ImagingUnitOfWork], pages: PageAccessPort, storage: FileStorage
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._storage = storage

    async def execute(
        self, identity: Identity | None, page_id: int, variant: ImageVariant
    ) -> DownloadedImage:
        access = await self._pages.get_page(identity, page_id)
        async with self._uow_factory() as uow:
            translation = await uow.translations.get(access.translation_id) if access.translation_id else None
            if variant is not ImageVariant.ORIGINAL and (
                translation is None or translation.status is not TranslationStatus.DONE
            ):
                raise ImageNotReadyError()
            file_id = variant_file_id(variant, access.original_file_id, translation)
            if file_id is None:
                raise ImageNotReadyError()
            stored = await uow.files.get(file_id)
        if stored is None or stored.removed_at is not None:
            raise ImageFileNotFoundError()
        number = None if access.chapter_number is None else format(access.chapter_number.normalize(), "f")
        filename = download_filename(
            access.series_title, number, access.page_no, variant.value, stored.storage_key.rsplit(".", 1)[-1]
        )
        return DownloadedImage(await self._storage.read(stored.storage_key), stored.mime_type, filename)
