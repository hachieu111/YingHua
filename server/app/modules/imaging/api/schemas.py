from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.core.uploads import file_url
from app.modules.imaging.application.dto import PageStatus, RequeueResult, TranslationList
from app.modules.imaging.domain.entities import Translation


class RequeueResponse(BaseModel):
    page_id: int | None
    translation_id: int
    status: str

    @classmethod
    def from_result(cls, r: RequeueResult) -> RequeueResponse:
        return cls(page_id=r.page_id, translation_id=r.translation_id, status=r.status.value)


class PageStatusResponse(BaseModel):
    page_id: int
    translation_id: int | None
    status: str | None
    attempts: int
    error_step: str | None
    error_message: str | None
    can_retranslate: bool
    text_ready: bool

    @classmethod
    def from_status(cls, s: PageStatus) -> PageStatusResponse:
        return cls(
            page_id=s.page_id,
            translation_id=s.translation_id,
            status=s.status.value if s.status else None,
            attempts=s.attempts,
            error_step=s.error_step,
            error_message=s.error_message,
            can_retranslate=s.can_retranslate,
            text_ready=s.text_ready,
        )


class AdminTranslationResponse(BaseModel):
    id: int
    status: str
    attempts: int
    worker_id: str | None
    error_step: str | None
    error_message: str | None
    original_url: str | None
    inpainted_url: str | None
    rendered_url: str | None
    processing_ms: int | None
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def from_entity(cls, t: Translation) -> AdminTranslationResponse:
        return cls(
            id=t.id,
            status=t.status.value,
            attempts=t.attempts,
            worker_id=t.worker_id,
            error_step=t.error_step,
            error_message=t.error_message,
            original_url=file_url(t.source_file_id),
            inpainted_url=file_url(t.inpainted_file_id),
            rendered_url=file_url(t.rendered_file_id),
            processing_ms=t.processing_ms,
            queued_at=t.queued_at,
            started_at=t.started_at,
            finished_at=t.finished_at,
        )


class AdminTranslationPage(BaseModel):
    items: list[AdminTranslationResponse]
    total: int
    page: int
    size: int
    counts: dict[str, int]
    avg_processing_ms: int | None

    @classmethod
    def from_list(cls, result: TranslationList, page: int, size: int) -> AdminTranslationPage:
        return cls(
            items=[AdminTranslationResponse.from_entity(t) for t in result.items],
            total=result.total,
            page=page,
            size=size,
            counts=result.stats.counts,
            avg_processing_ms=result.stats.avg_processing_ms,
        )
