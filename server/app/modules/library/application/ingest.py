"""Nhập một ảnh trang vào hệ thống: lưu tệp gốc và gắn bản dịch (dùng lại hoặc xếp hàng mới)."""

from __future__ import annotations

from datetime import datetime

from app.core.image_validation import ImageUpload
from app.core.storage import StagedFiles
from app.core.stored_files import FileKind, StoredFile, store_image
from app.modules.library.application.ports import LibraryUnitOfWork


async def ingest_page_image(
    uow: LibraryUnitOfWork,
    staged: StagedFiles,
    upload: ImageUpload,
    owner_id: int,
    now: datetime,
    expires_at: datetime | None = None,
) -> tuple[StoredFile, int]:
    """Lưu ảnh gốc, rồi dùng lại bản dịch `done` của ảnh cùng nội dung (F04.14) hoặc xếp hàng mới (F04.01).

    Trả (tệp đã lưu, mã bản dịch).
    """
    stored = await store_image(staged, uow.files, upload, FileKind.ORIGINAL, owner_id, now, expires_at)
    translation_id = await uow.translations.find_done_by_sha256(upload.info.sha256)
    if translation_id is None:
        translation_id = await uow.translations.enqueue(stored.id, upload.info.sha256, now)
    return stored, translation_id
