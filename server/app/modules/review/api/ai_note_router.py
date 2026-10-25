"""Thẻ mở rộng AI của mục từ (F08.11, US-NH-75)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.modules.auth.api.public import Identity, get_identity
from app.modules.review.api.dependencies import ReviewServices, get_review_services
from app.modules.review.application.dto import AiNoteView

router = APIRouter(prefix="/vocab-entries", tags=["M08 Ôn tập"])


class AiExampleResponse(BaseModel):
    zh: str
    pinyin: str | None
    vi: str | None


class AiNoteResponse(BaseModel):
    vocab_entry_id: int
    source: str = Field(description="llm (do AI tạo) | fallback (từ từ điển M06)")
    source_label: str = Field(description='Nhãn hiển thị: "Do AI tạo" hoặc "Từ từ điển"')
    examples: list[AiExampleResponse] = Field(description="0–2 câu ví dụ; rỗng thì ẩn phần này")
    mnemonic: str | None = Field(description="Mẹo nhớ theo chiết tự; null thì ẩn phần này")
    phrases: list[AiExampleResponse] = Field(description="0–3 cụm từ đi kèm (zh, pinyin, vi)")
    generated_at: datetime
    regenerate_count: int
    regenerate_remaining: int = Field(description="Số lượt Tạo lại còn lại cho từ này")

    @classmethod
    def from_view(cls, view: AiNoteView) -> AiNoteResponse:
        note = view.note
        llm = note.source.value == "llm"
        return cls(
            vocab_entry_id=note.vocab_entry_id,
            source=note.source.value,
            source_label="Do AI tạo" if llm else "Từ từ điển",
            examples=[AiExampleResponse(zh=e.zh, pinyin=e.pinyin, vi=e.vi) for e in note.content.examples],
            mnemonic=note.content.mnemonic,
            phrases=[AiExampleResponse(zh=p.zh, pinyin=p.pinyin, vi=p.vi) for p in note.content.phrases],
            generated_at=note.generated_at,
            regenerate_count=note.regenerate_count,
            regenerate_remaining=view.regenerate_remaining,
        )


@router.get(
    "/{entry_id}/ai-note",
    response_model=AiNoteResponse,
    summary="Thẻ mở rộng AI của mục từ: ví dụ, mẹo chiết tự, cụm đi kèm (F08.11)",
    description=(
        "Trả bản đã lưu; chưa có thì tạo rồi trả. LLM tắt/lỗi/hết hạn mức ngày vẫn trả 200 với nội dung dự "
        "phòng (`source=fallback`), không báo lỗi kỹ thuật. Từ của người khác → 404."
    ),
)
async def get_ai_note(
    entry_id: int,
    identity: Identity = Depends(get_identity),
    services: ReviewServices = Depends(get_review_services),
) -> AiNoteResponse:
    return AiNoteResponse.from_view(await services.ai_note.execute(identity, entry_id))


@router.post(
    "/{entry_id}/ai-note/regenerate",
    response_model=AiNoteResponse,
    summary="Tạo lại Thẻ mở rộng AI, giới hạn số lần cho mỗi từ (F08.11)",
    description="Vượt giới hạn → 429 `AI_NOTE_REGENERATE_LIMIT`, nội dung hiện có được giữ nguyên.",
)
async def regenerate_ai_note(
    entry_id: int,
    identity: Identity = Depends(get_identity),
    services: ReviewServices = Depends(get_review_services),
) -> AiNoteResponse:
    return AiNoteResponse.from_view(await services.ai_note.execute(identity, entry_id, regenerate=True))
