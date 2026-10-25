from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.image_validation import validate_image
from app.core.storage import FileStorage, StagedFiles
from app.core.stored_files import FileKind, store_image
from app.modules.imaging.application.ports import ImagingUnitOfWork
from app.modules.imaging.domain.errors import InvalidResultKindError
from app.modules.imaging.domain.rules import MAX_RESULT_IMAGE_BYTES

_RESULT_KINDS = frozenset({FileKind.INPAINTED, FileKind.RENDERED})
_RESULT_FILENAME = "result.png"  # chỉ để qua kiểm đuôi; định dạng thật do header ảnh quyết định


class StoreResultImageUseCase:
    """F04.11, F04.12 — Worker lưu ảnh đã xóa chữ / đã dịch vào kho tệp, trả mã tệp để `complete_job` gắn vào.

    Không thuộc người dùng nào (`owner_id` rỗng) và không có hạn: vòng đời theo bản dịch; tệp mồ côi được
    dọn bởi F15.03.
    """

    def __init__(
        self, uow_factory: Callable[[], ImagingUnitOfWork], clock: Clock, storage: FileStorage
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._storage = storage

    async def execute(self, data: bytes, kind: FileKind) -> int:
        if kind not in _RESULT_KINDS:
            raise InvalidResultKindError()
        upload = await validate_image(data, _RESULT_FILENAME, MAX_RESULT_IMAGE_BYTES)
        staged = StagedFiles(self._storage)
        try:
            async with self._uow_factory() as uow:
                stored = await store_image(staged, uow.files, upload, kind, None, self._clock.now())
                await uow.commit()
        except BaseException:
            await staged.discard()
            raise
        return stored.id
