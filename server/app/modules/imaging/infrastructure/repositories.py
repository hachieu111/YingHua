from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import and_, delete, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.stored_files import FileKind, StoredFileModel
from app.modules.imaging.application.dto import TranslationSummary
from app.modules.imaging.domain.entities import (
    PIPELINE_VERSION,
    Bubble,
    NewBubble,
    QueueStats,
    Translation,
    TranslationStatus,
)
from app.modules.imaging.infrastructure.orm_models import BubbleModel, TranslationModel

_QUEUED = TranslationStatus.QUEUED.value
_RUNNING = TranslationStatus.RUNNING.value
_DONE = TranslationStatus.DONE.value
_FAILED = TranslationStatus.FAILED.value


def _translation(m: TranslationModel) -> Translation:
    return Translation(
        id=m.id,
        source_file_id=m.source_file_id,
        sha256=m.sha256,
        status=TranslationStatus(m.status),
        pipeline_version=m.pipeline_version,
        attempts=m.attempts,
        queued_at=m.queued_at,
        phash=m.phash,
        worker_id=m.worker_id,
        error_step=m.error_step,
        error_message=m.error_message,
        inpainted_file_id=m.inpainted_file_id,
        rendered_file_id=m.rendered_file_id,
        stats=dict(m.stats or {}),
        processing_ms=m.processing_ms,
        started_at=m.started_at,
        finished_at=m.finished_at,
    )


def _bubble(m: BubbleModel) -> Bubble:
    return Bubble(
        id=m.id,
        translation_id=m.translation_id,
        idx=m.idx,
        class_name=m.class_name,
        x=m.x,
        y=m.y,
        w=m.w,
        h=m.h,
        text_zh=m.text_zh,
        polygon=m.polygon,
        confidence=m.confidence,
        pinyin=m.pinyin,
        text_vi=m.text_vi,
        translate_method=m.translate_method,
        lines=list(m.lines or []),
        tokens=list(m.tokens or []),
        style=m.style,
    )


class SqlTranslationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(self, source_file_id: int, sha256: str, now: datetime) -> int:
        model = TranslationModel(
            source_file_id=source_file_id,
            sha256=sha256,
            status=_QUEUED,
            pipeline_version=PIPELINE_VERSION,
            queued_at=now,
        )
        self._session.add(model)
        await self._session.flush()
        return model.id

    async def find_done_by_sha256(self, sha256: str) -> int | None:
        row = await self._session.execute(
            select(TranslationModel.id)
            .where(
                TranslationModel.sha256 == sha256,
                TranslationModel.status == _DONE,
                TranslationModel.pipeline_version == PIPELINE_VERSION,
            )
            .order_by(TranslationModel.id.desc())
            .limit(1)
        )
        return row.scalar_one_or_none()

    async def get_summaries(self, translation_ids: Sequence[int]) -> dict[int, TranslationSummary]:
        if not translation_ids:
            return {}
        rows = await self._session.execute(
            select(TranslationModel).where(TranslationModel.id.in_(list(translation_ids)))
        )
        return {
            m.id: TranslationSummary(
                id=m.id,
                status=TranslationStatus(m.status),
                inpainted_file_id=m.inpainted_file_id,
                rendered_file_id=m.rendered_file_id,
                error_step=m.error_step,
                error_message=m.error_message,
            )
            for m in rows.scalars()
        }

    async def translation_ids_of_file(self, file_id: int) -> list[int]:
        rows = await self._session.execute(
            select(TranslationModel.id).where(
                or_(
                    TranslationModel.inpainted_file_id == file_id,
                    TranslationModel.rendered_file_id == file_id,
                )
            )
        )
        return list(rows.scalars())

    async def delete_many(self, translation_ids: Sequence[int]) -> list[int]:
        if not translation_ids:
            return []
        rows = await self._session.execute(
            delete(TranslationModel)
            .where(TranslationModel.id.in_(list(translation_ids)))
            .returning(TranslationModel.inpainted_file_id, TranslationModel.rendered_file_id)
        )
        return [fid for pair in rows.all() for fid in pair if fid is not None]

    async def get(self, translation_id: int) -> Translation | None:
        model = await self._session.get(TranslationModel, translation_id)
        return _translation(model) if model else None

    async def get_for_update(self, translation_id: int) -> Translation | None:
        row = await self._session.execute(
            select(TranslationModel).where(TranslationModel.id == translation_id).with_for_update()
        )
        model = row.scalar_one_or_none()
        return _translation(model) if model else None

    async def requeue_failed(self, translation_id: int, now: datetime) -> bool:
        row = await self._session.execute(
            update(TranslationModel)
            .where(TranslationModel.id == translation_id, TranslationModel.status == _FAILED)
            .values(
                status=_QUEUED,
                attempts=0,
                worker_id=None,
                error_step=None,
                error_message=None,
                queued_at=now,
                started_at=None,
                finished_at=None,
            )
            .returning(TranslationModel.id)
        )
        return row.scalar_one_or_none() is not None

    async def claim_next(self, worker_id: str, now: datetime, stale_before: datetime) -> Translation | None:
        row = await self._session.execute(
            select(TranslationModel)
            .where(
                or_(
                    TranslationModel.status == _QUEUED,
                    and_(TranslationModel.status == _RUNNING, TranslationModel.started_at < stale_before),
                )
            )
            .order_by(TranslationModel.queued_at, TranslationModel.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        model = row.scalar_one_or_none()
        if model is None:
            return None
        model.status = _RUNNING
        model.started_at = now
        model.finished_at = None
        model.attempts = model.attempts + 1
        model.worker_id = worker_id
        await self._session.flush()
        return _translation(model)

    async def fail_exhausted_stale(self, stale_before: datetime, now: datetime, max_attempts: int) -> int:
        rows = await self._session.execute(
            update(TranslationModel)
            .where(
                TranslationModel.status == _RUNNING,
                TranslationModel.started_at < stale_before,
                TranslationModel.attempts >= max_attempts,
            )
            .values(
                status=_FAILED,
                error_step="timeout",
                error_message="Xử lý quá thời gian cho phép, worker không phản hồi",
                finished_at=now,
            )
            .returning(TranslationModel.id)
        )
        return len(rows.all())

    async def mark_done(
        self,
        translation_id: int,
        inpainted_file_id: int | None,
        rendered_file_id: int | None,
        stats: dict[str, Any],
        processing_ms: int,
        phash: int | None,
        now: datetime,
    ) -> None:
        await self._session.execute(
            update(TranslationModel)
            .where(TranslationModel.id == translation_id)
            .values(
                status=_DONE,
                inpainted_file_id=inpainted_file_id,
                rendered_file_id=rendered_file_id,
                stats=stats,
                processing_ms=processing_ms,
                phash=phash,
                error_step=None,
                error_message=None,
                finished_at=now,
            )
        )

    async def mark_failed(
        self, translation_id: int, step: str, message: str, requeue: bool, now: datetime
    ) -> TranslationStatus:
        status = TranslationStatus.QUEUED if requeue else TranslationStatus.FAILED
        values: dict[str, Any] = {
            "status": status.value,
            "error_step": step,
            "error_message": message,
            "finished_at": None if requeue else now,
        }
        if requeue:
            values.update(started_at=None, worker_id=None)
        await self._session.execute(
            update(TranslationModel).where(TranslationModel.id == translation_id).values(**values)
        )
        return status

    async def list_page(
        self, status: TranslationStatus | None, offset: int, limit: int
    ) -> tuple[list[Translation], int]:
        conditions = [TranslationModel.status == status.value] if status else []
        total = await self._session.scalar(
            select(func.count()).select_from(TranslationModel).where(*conditions)
        )
        rows = await self._session.execute(
            select(TranslationModel)
            .where(*conditions)
            .order_by(TranslationModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_translation(m) for m in rows.scalars()], int(total or 0)

    async def stats(self) -> QueueStats:
        counts = {s.value: 0 for s in TranslationStatus}
        rows = await self._session.execute(
            select(TranslationModel.status, func.count()).group_by(TranslationModel.status)
        )
        for status, count in rows.all():
            counts[status] = count
        avg = await self._session.scalar(
            select(func.avg(TranslationModel.processing_ms)).where(TranslationModel.status == _DONE)
        )
        return QueueStats(counts=counts, avg_processing_ms=None if avg is None else round(float(avg)))

    async def orphan_result_file_ids(self, created_before: datetime, limit: int) -> list[int]:
        referenced = exists().where(
            or_(
                TranslationModel.inpainted_file_id == StoredFileModel.id,
                TranslationModel.rendered_file_id == StoredFileModel.id,
            )
        )
        rows = await self._session.execute(
            select(StoredFileModel.id)
            .where(
                StoredFileModel.kind.in_([FileKind.INPAINTED.value, FileKind.RENDERED.value]),
                StoredFileModel.created_at < created_before,
                ~referenced,
            )
            .order_by(StoredFileModel.id)
            .limit(limit)
        )
        return list(rows.scalars())


class SqlBubbleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_translation(self, translation_id: int) -> list[Bubble]:
        rows = await self._session.execute(
            select(BubbleModel).where(BubbleModel.translation_id == translation_id).order_by(BubbleModel.idx)
        )
        return [_bubble(m) for m in rows.scalars()]

    async def get(self, bubble_id: int) -> Bubble | None:
        model = await self._session.get(BubbleModel, bubble_id)
        return _bubble(model) if model else None

    async def get_many(self, bubble_ids: Sequence[int]) -> dict[int, Bubble]:
        if not bubble_ids:
            return {}
        rows = await self._session.execute(select(BubbleModel).where(BubbleModel.id.in_(list(bubble_ids))))
        return {m.id: _bubble(m) for m in rows.scalars()}

    async def delete_by_translation(self, translation_id: int) -> int:
        rows = await self._session.execute(
            delete(BubbleModel).where(BubbleModel.translation_id == translation_id).returning(BubbleModel.id)
        )
        return len(rows.all())

    async def add_many(self, translation_id: int, bubbles: Sequence[NewBubble]) -> None:
        self._session.add_all(
            BubbleModel(
                translation_id=translation_id,
                idx=b.idx,
                class_name=b.class_name,
                x=b.x,
                y=b.y,
                w=b.w,
                h=b.h,
                polygon=b.polygon,
                confidence=b.confidence,
                text_zh=b.text_zh,
                pinyin=b.pinyin,
                text_vi=b.text_vi,
                translate_method=b.translate_method,
                lines=list(b.lines),
                tokens=list(b.tokens),
                style=b.style,
            )
            for b in bubbles
        )
        await self._session.flush()
