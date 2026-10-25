"""Bảng `stored_files` dùng chung (docs/database-design.md §4.5): thực thể, port và repository.

Đặt trong `core/` vì nhiều module cùng ghi tệp (M01 avatar, M03 trang/bìa, M04 ảnh dẫn xuất, M07/M11).
CSDL chỉ giữ khóa tương đối tới FileStorage, không giữ nhị phân.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    delete,
    func,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.image_validation import ImageUpload
from app.core.storage import StagedFiles


class FileKind(str, Enum):
    ORIGINAL = "original"
    INPAINTED = "inpainted"
    RENDERED = "rendered"
    SNIPPET = "snippet"
    COVER = "cover"
    AUDIO = "audio"
    AVATAR = "avatar"


@dataclass(slots=True)
class StoredFile:
    id: int
    kind: FileKind
    storage_key: str
    sha256: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    width: int | None = None
    height: int | None = None
    owner_id: int | None = None
    expires_at: datetime | None = None
    removed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class NewStoredFile:
    kind: FileKind
    storage_key: str
    sha256: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    width: int | None = None
    height: int | None = None
    owner_id: int | None = None
    expires_at: datetime | None = None


class StoredFileRepository(Protocol):
    async def add(self, new_file: NewStoredFile) -> StoredFile: ...

    async def get(self, file_id: int) -> StoredFile | None: ...

    async def delete_many(self, file_ids: Sequence[int]) -> list[str]:
        """Xóa dòng; trả khóa lưu trữ để xóa tệp thật sau khi commit."""
        ...


class StoredFileModel(Base):
    __tablename__ = "stored_files"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('original', 'inpainted', 'rendered', 'snippet', 'cover', 'audio', 'avatar')",
            name="kind",
        ),
        Index("ix_stored_files_sha256", "sha256"),
        Index("ix_stored_files_owner_id", "owner_id"),
        Index(
            "ix_stored_files_expires_at",
            "expires_at",
            postgresql_where="expires_at IS NOT NULL",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    storage_key: Mapped[str] = mapped_column(Text, unique=True)
    sha256: Mapped[str] = mapped_column(CHAR(64))
    mime_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    owner_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def _entity(m: StoredFileModel) -> StoredFile:
    return StoredFile(
        id=m.id,
        kind=FileKind(m.kind),
        storage_key=m.storage_key,
        sha256=m.sha256,
        mime_type=m.mime_type,
        size_bytes=m.size_bytes,
        created_at=m.created_at,
        width=m.width,
        height=m.height,
        owner_id=m.owner_id,
        expires_at=m.expires_at,
        removed_at=m.removed_at,
    )


class SqlStoredFileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, new_file: NewStoredFile) -> StoredFile:
        model = StoredFileModel(
            kind=new_file.kind.value,
            storage_key=new_file.storage_key,
            sha256=new_file.sha256,
            mime_type=new_file.mime_type,
            size_bytes=new_file.size_bytes,
            width=new_file.width,
            height=new_file.height,
            owner_id=new_file.owner_id,
            expires_at=new_file.expires_at,
            created_at=new_file.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _entity(model)

    async def get(self, file_id: int) -> StoredFile | None:
        model = await self._session.get(StoredFileModel, file_id)
        return _entity(model) if model else None

    async def delete_many(self, file_ids: Sequence[int]) -> list[str]:
        if not file_ids:
            return []
        rows = await self._session.execute(
            delete(StoredFileModel)
            .where(StoredFileModel.id.in_(list(file_ids)))
            .returning(StoredFileModel.storage_key)
        )
        return [key for (key,) in rows.all()]


async def store_image(
    staged: StagedFiles,
    files: StoredFileRepository,
    upload: ImageUpload,
    kind: FileKind,
    owner_id: int | None,
    now: datetime,
    expires_at: datetime | None = None,
) -> StoredFile:
    """Ghi tệp vào kho rồi ghi dòng `stored_files` (cùng giao dịch của người gọi).

    Người gọi chịu trách nhiệm gọi `staged.discard()` nếu giao dịch không commit.
    """
    info = upload.info
    key = await staged.save(upload.data, kind.value, info.extension)
    return await files.add(
        NewStoredFile(
            kind=kind,
            storage_key=key,
            sha256=info.sha256,
            mime_type=info.mime_type,
            size_bytes=info.size_bytes,
            created_at=now,
            width=info.width,
            height=info.height,
            owner_id=owner_id,
            expires_at=expires_at,
        )
    )
