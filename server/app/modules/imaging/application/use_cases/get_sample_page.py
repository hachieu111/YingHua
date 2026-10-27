from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.core.errors import NotFoundError
from app.modules.admin.application.public import SystemSettingsPort
from app.modules.auth.application.public import Identity
from app.modules.imaging.application.ports import ImagingUnitOfWork
from app.modules.imaging.domain.entities import Bubble, Translation, TranslationStatus
from app.modules.imaging.domain.errors import SamplePageNotConfiguredError
from app.modules.library.application.public import PageAccess, PageAccessPort


@dataclass(frozen=True, slots=True)
class SamplePage:
    access: PageAccess
    translation: Translation
    bubbles: list[Bubble]


class GetSamplePageUseCase:
    """F04.16 — Thử với trang mẫu (US-NH-77): kết quả xử lý thật của trang quản trị chọn (`sample_page_id`).

    Chỉ người đã đăng nhập. Chưa cấu hình, trang không còn đọc được, chưa dịch xong hoặc ảnh đã bị gỡ
    (F13.04) đều coi là chưa có trang mẫu (404). Không tạo công việc xử lý nào.
    """

    def __init__(
        self,
        uow_factory: Callable[[], ImagingUnitOfWork],
        pages: PageAccessPort,
        settings: SystemSettingsPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._settings = settings

    async def execute(self, identity: Identity) -> SamplePage:
        page_id = (await self._settings.snapshot()).sample_page_id
        if page_id is None:
            raise SamplePageNotConfiguredError()
        try:
            access = await self._pages.get_page(identity, page_id)
        except NotFoundError as exc:
            raise SamplePageNotConfiguredError() from exc
        if access.translation_id is None or access.original_file_id is None:
            raise SamplePageNotConfiguredError()
        async with self._uow_factory() as uow:
            translation = await uow.translations.get(access.translation_id)
            original = await uow.files.get(access.original_file_id)
            if (
                translation is None
                or translation.status is not TranslationStatus.DONE
                or original is None
                or original.removed_at is not None
            ):
                raise SamplePageNotConfiguredError()
            bubbles = await uow.bubbles.list_by_translation(translation.id)
        return SamplePage(access, translation, bubbles)
