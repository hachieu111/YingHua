from __future__ import annotations

from collections.abc import Callable

from app.core.errors import NotFoundError
from app.core.storage import FileStorage, StagedFiles
from app.modules.auth.application.dto import Identity
from app.modules.auth.application.ports import AuthUnitOfWork
from app.modules.auth.domain.entities import User
from app.modules.auth.domain.errors import InvalidAvatarPresetError
from app.modules.auth.domain.rules import AVATAR_PRESETS


class SetAvatarPresetUseCase:
    """F01.10 (mở rộng) — Chọn ảnh đại diện có sẵn (US-NH-65 TC6).

    Ghi `avatar_preset`, bỏ tham chiếu `avatar_file_id` và xóa tệp ảnh tải lên cũ (nếu có) sau khi commit.
    """

    def __init__(self, uow_factory: Callable[[], AuthUnitOfWork], storage: FileStorage) -> None:
        self._uow_factory = uow_factory
        self._storage = storage

    async def execute(self, identity: Identity, preset: str) -> User:
        if preset not in AVATAR_PRESETS:
            raise InvalidAvatarPresetError()
        staged = StagedFiles(self._storage)
        async with self._uow_factory() as uow:
            user = await uow.users.get(identity.user_id)
            if user is None:
                raise NotFoundError("Không tìm thấy tài khoản")
            old_id = user.avatar_file_id
            user.avatar_preset = preset
            user.avatar_file_id = None
            await uow.users.update(user)
            if old_id is not None:
                staged.delete_after_commit(await uow.files.delete_many([old_id]))
            await uow.commit()
        await staged.finalize()
        return user
