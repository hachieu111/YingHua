"""Cổng lưu trữ tệp (`FileStorage`) và hiện thực dùng hệ thống tệp cục bộ.

Khóa lưu trữ là đường dẫn tương đối `thư_mục/xx/<ngẫu nhiên>.<đuôi>`; tên tệp của người dùng không bao giờ
được dùng làm đường dẫn. Có thể đổi sang S3/MinIO bằng adapter mới.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import secrets
from pathlib import Path
from typing import Protocol

from app.core.errors import ExternalServiceError, NotFoundError

logger = logging.getLogger(__name__)

_FOLDER_RE = re.compile(r"^[a-z0-9_]{1,32}$")
_EXTENSION_RE = re.compile(r"^[a-z0-9]{1,8}$")


class StorageError(ExternalServiceError):
    code = "STORAGE_UNAVAILABLE"
    default_message = "Không ghi được tệp, vui lòng thử lại sau"


class FileStorage(Protocol):
    async def save(self, data: bytes, folder: str, extension: str) -> str:
        """Lưu `data` với tên ngẫu nhiên; trả khóa tương đối."""
        ...

    async def read(self, key: str) -> bytes:
        """Raise NotFoundError nếu không còn tệp."""
        ...

    async def delete(self, key: str) -> None:
        """Xóa tệp; không lỗi nếu tệp đã mất."""
        ...


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def _resolve(self, key: str) -> Path:
        path = (self._root / key).resolve()
        # Chống path traversal: đường dẫn sau khi chuẩn hóa phải nằm trong thư mục gốc.
        if not path.is_relative_to(self._root) or path == self._root:
            raise StorageError("Khóa tệp không hợp lệ")
        return path

    async def save(self, data: bytes, folder: str, extension: str) -> str:
        if not _FOLDER_RE.match(folder) or not _EXTENSION_RE.match(extension):
            raise StorageError("Thư mục hoặc đuôi tệp không hợp lệ")
        token = secrets.token_hex(16)
        key = f"{folder}/{token[:2]}/{token}.{extension}"
        path = self._resolve(key)
        try:
            await asyncio.to_thread(self._write, path, data)
        except OSError as exc:
            logger.error("Không ghi được tệp lưu trữ: %s", exc.__class__.__name__)
            raise StorageError() from exc
        return key

    @staticmethod
    def _write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".part")
        tmp.write_bytes(data)
        os.replace(tmp, path)  # đổi tên nguyên tử: không bao giờ để lại tệp ghi dở dưới tên thật

    async def read(self, key: str) -> bytes:
        path = self._resolve(key)
        try:
            return await asyncio.to_thread(path.read_bytes)
        except FileNotFoundError as exc:
            raise NotFoundError("Tệp không còn tồn tại") from exc
        except OSError as exc:
            raise StorageError() from exc

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        try:
            await asyncio.to_thread(path.unlink, True)
        except OSError as exc:
            logger.warning("Không xóa được tệp lưu trữ: %s", exc.__class__.__name__)


class StagedFiles:
    """Theo dõi tệp trong một use case có cả ghi tệp lẫn giao dịch CSDL.

    - `save`: ghi tệp ngay, nhớ lại để xóa nếu giao dịch thất bại (`discard`).
    - `delete_after_commit`: tệp cần xóa, chỉ thực sự xóa khi giao dịch đã commit (`finalize`).
    """

    def __init__(self, storage: FileStorage) -> None:
        self._storage = storage
        self._written: list[str] = []
        self._to_delete: list[str] = []

    async def save(self, data: bytes, folder: str, extension: str) -> str:
        key = await self._storage.save(data, folder, extension)
        self._written.append(key)
        return key

    def delete_after_commit(self, keys: list[str]) -> None:
        self._to_delete.extend(keys)

    async def discard(self) -> None:
        for key in self._written:
            await self._storage.delete(key)
        self._written.clear()
        self._to_delete.clear()

    async def finalize(self) -> None:
        for key in self._to_delete:
            await self._storage.delete(key)
        self._to_delete.clear()
        self._written.clear()
