from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.errors import NotFoundError
from app.core.image_validation import ImageUpload
from app.core.storage import FileStorage, StagedFiles
from app.core.stored_files import FileKind, store_image
from app.modules.auth.application.dto import Identity
from app.modules.auth.application.ports import AuthUnitOfWork
from app.modules.auth.domain.entities import User


class UploadAvatarUseCase:
    """F01.10 — Tải ảnh đại diện (US-NH-65). Ảnh mới thay ảnh cũ; ảnh đã được kiểm tra ở tầng api."""

    def __init__(self, uow_factory: Callable[[], AuthUnitOfWork], clock: Clock, storage: FileStorage) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._storage = storage

    async def execute(self, identity: Identity, upload: ImageUpload) -> User:
        staged = StagedFiles(self._storage)
        try:
            async with self._uow_factory() as uow:
                user = await uow.users.get(identity.user_id)
                if user is None:
                    raise NotFoundError("Không tìm thấy tài khoản")
                stored = await store_image(
                    staged, uow.files, upload, FileKind.AVATAR, user.id, self._clock.now()
                )
                old_id = user.avatar_file_id
                user.avatar_file_id = stored.id
                user.avatar_preset = None  # tải ảnh lên và ảnh có sẵn loại trừ nhau (F01.10)
                await uow.users.update(user)
                if old_id is not None:
                    staged.delete_after_commit(await uow.files.delete_many([old_id]))
                await uow.commit()
        except BaseException:
            await staged.discard()
            raise
        await staged.finalize()
        return user
