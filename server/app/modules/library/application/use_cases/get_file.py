from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.storage import FileStorage
from app.core.stored_files import FileKind
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import actor_of
from app.modules.library.application.dto import FileContent
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.errors import FileExpiredError, FileNotFoundForUserError
from app.modules.library.domain.rules import can_view_file

_DERIVED_KINDS = frozenset({FileKind.INPAINTED, FileKind.RENDERED})


class GetFileUseCase:
    """F03.10, F03.03, F01.10 — Phục vụ tệp ảnh có kiểm quyền; tệp bị gỡ (F13.04) hoặc không đủ quyền → 404.

    Không bao giờ trả đường dẫn trên máy chủ; chỉ trả nội dung.
    """

    def __init__(
        self, uow_factory: Callable[[], LibraryUnitOfWork], clock: Clock, storage: FileStorage
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._storage = storage

    async def execute(self, identity: Identity | None, file_id: int) -> FileContent:
        actor = actor_of(identity)
        async with self._uow_factory() as uow:
            stored = await uow.files.get(file_id)
            if stored is None or stored.removed_at is not None:
                raise FileNotFoundForUserError()
            translation_ids = (
                await uow.translations.translation_ids_of_file(file_id)
                if stored.kind in _DERIVED_KINDS
                else []
            )
            contexts = await uow.pages.file_contexts(file_id, translation_ids)
        if not can_view_file(stored.kind.value, stored.owner_id, contexts, actor):
            raise FileNotFoundForUserError()
        if stored.expires_at is not None and stored.expires_at <= self._clock.now():
            raise FileExpiredError()
        return FileContent(await self._storage.read(stored.storage_key), stored.mime_type)
