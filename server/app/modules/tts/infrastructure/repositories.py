from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.storage import FileStorage, StagedFiles
from app.core.stored_files import FileKind, NewStoredFile, SqlStoredFileRepository, StoredFileModel
from app.modules.tts.application.ports import CachedAudio
from app.modules.tts.infrastructure.orm_models import TtsCacheModel

AUDIO_MIME = "audio/mpeg"
AUDIO_EXTENSION = "mp3"


class SqlTtsCacheRepository:
    """Bộ đệm âm thanh: dòng `tts_cache` + `stored_files` (kind audio, không hết hạn) + tệp trong FileStorage.

    Mỗi thao tác dùng giao dịch riêng nên use case không phải giữ kết nối trong lúc chờ Edge TTS.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], storage: FileStorage) -> None:
        self._session_factory = session_factory
        self._storage = storage

    async def find(self, text_sha256: str, voice: str, rate: Decimal) -> CachedAudio | None:
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    select(TtsCacheModel.id, StoredFileModel.storage_key)
                    .join(StoredFileModel, StoredFileModel.id == TtsCacheModel.file_id)
                    .where(
                        TtsCacheModel.text_sha256 == text_sha256,
                        TtsCacheModel.voice == voice,
                        TtsCacheModel.rate == rate,
                    )
                )
            ).first()
        return CachedAudio(cache_id=row[0], storage_key=row[1]) if row else None

    async def read(self, cached: CachedAudio) -> bytes:
        return await self._storage.read(cached.storage_key)

    async def store(
        self, text_sha256: str, voice: str, rate: Decimal, audio: bytes, now: datetime
    ) -> CachedAudio:
        staged = StagedFiles(self._storage)
        try:
            async with self._session_factory() as session, session.begin():
                cached = await self._upsert(session, staged, text_sha256, voice, rate, audio, now)
        except BaseException:
            await staged.discard()
            raise
        await staged.finalize()
        return cached

    async def _upsert(
        self,
        session: AsyncSession,
        staged: StagedFiles,
        text_sha256: str,
        voice: str,
        rate: Decimal,
        audio: bytes,
        now: datetime,
    ) -> CachedAudio:
        files = SqlStoredFileRepository(session)
        old_file_id = (
            await session.execute(
                select(TtsCacheModel.file_id)
                .where(
                    TtsCacheModel.text_sha256 == text_sha256,
                    TtsCacheModel.voice == voice,
                    TtsCacheModel.rate == rate,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        key = await staged.save(audio, FileKind.AUDIO.value, AUDIO_EXTENSION)
        new_file = await files.add(
            NewStoredFile(
                kind=FileKind.AUDIO,
                storage_key=key,
                sha256=hashlib.sha256(audio).hexdigest(),
                mime_type=AUDIO_MIME,
                size_bytes=len(audio),
                created_at=now,
            )
        )
        # UNIQUE (text_sha256, voice, rate) chống trùng giữa các tiến trình: bên thua cuộc chỉ thay tệp.
        cache_id = (
            await session.execute(
                pg_insert(TtsCacheModel)
                .values(text_sha256=text_sha256, voice=voice, rate=rate, file_id=new_file.id, created_at=now)
                .on_conflict_do_update(
                    index_elements=["text_sha256", "voice", "rate"], set_={"file_id": new_file.id}
                )
                .returning(TtsCacheModel.id)
            )
        ).scalar_one()
        if old_file_id is not None and old_file_id != new_file.id:
            # Xóa tệp cũ sau khi dòng bộ đệm đã trỏ sang tệp mới (khóa ngoại CASCADE sẽ không động tới nó).
            staged.delete_after_commit(await files.delete_many([old_file_id]))
        return CachedAudio(cache_id=cache_id, storage_key=key)
