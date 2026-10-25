"""Phần tầng api dùng chung cho tải ảnh lên: đọc tệp có giới hạn, kiểm tra, và dựng URL tệp."""

from __future__ import annotations

from fastapi import UploadFile

from app.core.errors import DomainError
from app.core.image_validation import ImageTooLargeError, ImageUpload, UploadAttempt, validate_image

FILES_URL_PREFIX = "/api/v1/files"


async def read_image_upload(file: UploadFile, max_bytes: int) -> ImageUpload:
    """Đọc tối đa `max_bytes + 1` byte (không nạp tệp khổng lồ vào RAM) rồi kiểm tra ảnh (F03.07, F01.10)."""
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ImageTooLargeError(f"Ảnh vượt quá {max_bytes // (1024 * 1024)} MB")
    return await validate_image(data, file.filename, max_bytes)


async def read_image_uploads(files: list[UploadFile], max_bytes: int) -> list[UploadAttempt]:
    """Kiểm tra từng tệp riêng: một tệp lỗi không làm hỏng các tệp hợp lệ khác trong lượt tải (F03.07)."""
    attempts: list[UploadAttempt] = []
    for file in files:
        try:
            attempts.append(UploadAttempt(file.filename, upload=await read_image_upload(file, max_bytes)))
        except DomainError as exc:
            attempts.append(UploadAttempt(file.filename, error=exc))
    return attempts


def file_url(file_id: int | None) -> str | None:
    """Địa chỉ phục vụ tệp (có kiểm quyền); không bao giờ là đường dẫn trên máy chủ."""
    return None if file_id is None else f"{FILES_URL_PREFIX}/{file_id}"
