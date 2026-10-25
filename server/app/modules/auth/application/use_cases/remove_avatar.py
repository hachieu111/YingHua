from __future__ import annotations

from collections.abc import Callable

from app.core.errors import NotFoundError
from app.core.storage import FileStorage, StagedFiles
from app.modules.auth.application.dto import Identity
from app.modules.auth.application.ports import AuthUnitOfWork


class RemoveAvatarUseCase:
    """F01.10 — Xóa ảnh đại diện (US-NH-65): gỡ tham chiếu `users.avatar_file_id` và xóa tệp khỏi kho.

    Idempotent: chưa có ảnh đại diện thì không làm gì. Tệp thật chỉ bị xóa sau khi giao dịch commit.
    """

    def __init__(self, uow_factory: Callable[[], AuthUnitOfWork], storage: FileStorage) -> None:
        self._uow_factory = uow_factory
        self._storage = storage

    async def execute(self, identity: Identity) -> None:
        staged = StagedFiles(self._storage)
        async with self._uow_factory() as uow:
            user = await uow.users.get(identity.user_id)
            if user is None:
                raise NotFoundError("Không tìm thấy tài khoản")
            old_id = user.avatar_file_id
            if old_id is None:
                return
            user.avatar_file_id = None
            await uow.users.update(user)
            staged.delete_after_commit(await uow.files.delete_many([old_id]))
            await uow.commit()
        await staged.finalize()
