from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.uploads import file_url
from app.modules.review.application.dto import (
    ContextFace,
    DueBatch,
    DueCard,
    GradeResult,
    HistoryPage,
    ReviewSummary,
)
from app.modules.review.application.sides import CardSide, sides_for
from app.modules.review.domain.entities import Card, ReviewLog


class GradeRequest(BaseModel):
    rating: int = Field(description="1 Quên · 2 Khó · 3 Được · 4 Dễ (giá trị khác → 400 INVALID_RATING)")
    presentation_id: uuid.UUID = Field(
        description="Mã lượt hiển thị thẻ do trình duyệt sinh (UUID); gửi lại cùng mã chỉ tính một lượt ôn"
    )
    duration_ms: int | None = Field(
        default=None, ge=0, le=3_600_000, description="Thời gian nghĩ trước khi chấm"
    )
    deck: str | None = Field(default=None, max_length=32, description="Bộ thẻ để chọn thẻ kế tiếp")


class CardSideResponse(BaseModel):
    term: str | None
    pinyin: str | None
    meaning_vi: str | None
    sino_vietnamese: str | None
    audio_text: str | None = Field(description="Chữ cần phát âm (thẻ nghe); phát qua M11 TTS")
    sentence_vi: str | None = Field(
        default=None, description="Câu dịch của ngữ cảnh mới nhất; chỉ có khi gợi ý dự phòng của thẻ recall"
    )
    hint_source: Literal["meaning", "context_sentence", "sino_vietnamese", "pinyin"] | None = Field(
        default=None,
        description=(
            "Chỉ mặt trước thẻ recall: trường đang chứa gợi ý (meaning -> meaning_vi, "
            "context_sentence -> sentence_vi, sino_vietnamese, pinyin); null nếu không có gợi ý "
            "hoặc không phải thẻ recall"
        ),
    )

    @classmethod
    def from_side(cls, s: CardSide) -> CardSideResponse:
        return cls(
            term=s.term,
            pinyin=s.pinyin,
            meaning_vi=s.meaning_vi,
            sino_vietnamese=s.sino_vietnamese,
            audio_text=s.audio_text,
            sentence_vi=s.sentence_vi,
            hint_source=s.hint_source,
        )


class CardContextResponse(BaseModel):
    id: int
    snippet_url: str | None
    sentence_zh: str
    sentence_vi: str | None
    source_label: str | None

    @classmethod
    def from_face(cls, c: ContextFace) -> CardContextResponse:
        return cls(
            id=c.context_id,
            snippet_url=file_url(c.snippet_file_id),
            sentence_zh=c.sentence_zh,
            sentence_vi=c.sentence_vi,
            source_label=c.source_label,
        )


class CardStateResponse(BaseModel):
    id: int
    vocab_entry_id: int
    card_type: str = Field(description="recognition | recall | listening")
    state: str = Field(description="learning | review | relearning")
    due_at: datetime
    last_review_at: datetime | None
    stability: float | None
    difficulty: float | None
    reps: int
    lapses: int
    is_suspended: bool

    @classmethod
    def from_card(cls, c: Card) -> CardStateResponse:
        s = c.schedule
        return cls(
            id=c.id,
            vocab_entry_id=c.vocab_entry_id,
            card_type=c.card_type.value,
            state=s.state.value,
            due_at=s.due_at,
            last_review_at=s.last_review_at,
            stability=s.stability,
            difficulty=s.difficulty,
            reps=c.reps,
            lapses=c.lapses,
            is_suspended=c.is_suspended,
        )


class DueCardResponse(CardStateResponse):
    """Thẻ kèm nội dung hai mặt (F08.03) và phần mặt sau chung: ảnh ngữ cảnh, ghi chú (F08.04)."""

    term: str
    hsk_level: int | None
    is_starred: bool
    front: CardSideResponse
    back: CardSideResponse
    note: str | None
    context: CardContextResponse | None = Field(description="Ngữ cảnh mới nhất; null nếu từ chưa có ngữ cảnh")
    contexts_count: int

    @classmethod
    def from_due(cls, d: DueCard) -> DueCardResponse:
        front, back = sides_for(d.card.card_type, d.face)
        base = CardStateResponse.from_card(d.card)
        return cls(
            **base.model_dump(),
            term=d.face.term,
            hsk_level=d.face.hsk_level,
            is_starred=d.face.is_starred,
            front=CardSideResponse.from_side(front),
            back=CardSideResponse.from_side(back),
            note=d.face.note,
            context=CardContextResponse.from_face(d.face.context) if d.face.context else None,
            contexts_count=d.face.contexts_count,
        )


class DueCardsResponse(BaseModel):
    total: int = Field(description="Tổng số thẻ đến hạn trong bộ thẻ")
    deck: str
    items: list[DueCardResponse]

    @classmethod
    def from_batch(cls, b: DueBatch) -> DueCardsResponse:
        return cls(total=b.total, deck=b.deck.key, items=[DueCardResponse.from_due(c) for c in b.cards])


class GradeResponse(BaseModel):
    card: CardStateResponse
    rating: int
    reviewed_at: datetime
    due_at: datetime = Field(description="Hạn ôn tiếp theo của thẻ vừa chấm")
    interval_seconds: int = Field(description="Khoảng cách từ lúc chấm đến hạn ôn tiếp theo")
    duplicate: bool = Field(description="true: mã lượt hiển thị đã dùng, trả kết quả cũ, không tính lượt mới")
    remaining_due: int = Field(description="Số thẻ còn đến hạn (không tính thẻ vừa chấm)")
    session_complete: bool
    next_card: DueCardResponse | None

    @classmethod
    def from_result(cls, r: GradeResult) -> GradeResponse:
        next_card = r.next_batch.cards[0] if r.next_batch.cards else None
        return cls(
            card=CardStateResponse.from_card(r.card),
            rating=int(r.rating),
            reviewed_at=r.reviewed_at,
            due_at=r.due_at,
            interval_seconds=r.interval_seconds,
            duplicate=r.duplicate,
            remaining_due=r.next_batch.total,
            session_complete=r.next_batch.total == 0,
            next_card=DueCardResponse.from_due(next_card) if next_card else None,
        )


class ReviewLogResponse(BaseModel):
    id: int
    rating: int
    state_before: str
    stability_before: float | None
    stability_after: float | None
    difficulty_before: float | None
    difficulty_after: float | None
    due_after: datetime
    duration_ms: int | None
    reviewed_at: datetime

    @classmethod
    def from_log(cls, log: ReviewLog) -> ReviewLogResponse:
        return cls(
            id=log.id,
            rating=int(log.rating),
            state_before=log.state_before.value,
            stability_before=log.stability_before,
            stability_after=log.stability_after,
            difficulty_before=log.difficulty_before,
            difficulty_after=log.difficulty_after,
            due_after=log.due_after,
            duration_ms=log.duration_ms,
            reviewed_at=log.reviewed_at,
        )


class HistoryResponse(BaseModel):
    card: CardStateResponse
    items: list[ReviewLogResponse]
    total: int
    page: int
    size: int

    @classmethod
    def from_page(cls, h: HistoryPage, page: int, size: int) -> HistoryResponse:
        return cls(
            card=CardStateResponse.from_card(h.card),
            items=[ReviewLogResponse.from_log(i) for i in h.items],
            total=h.total,
            page=page,
            size=size,
        )


class StatusCountsResponse(BaseModel):
    learning: int
    known: int
    ignored: int


class ReviewSummaryResponse(BaseModel):
    status: str = Field(description="no_cards | due | completed")
    reviewed_today: int = Field(description="Số lượt ôn trong ngày theo múi giờ của người học")
    due_now: int
    due_later_today: int = Field(description="Số thẻ sẽ đến hạn trước hết ngày hôm nay")
    next_due_at: datetime | None
    total_cards: int
    timezone: str
    due_words: int = Field(description="Số mục từ có ít nhất một thẻ đến hạn (cùng quy tắc với /cards/due)")
    status_counts: StatusCountsResponse = Field(description="Số mục từ theo trạng thái học")

    @classmethod
    def from_summary(cls, s: ReviewSummary) -> ReviewSummaryResponse:
        counts = StatusCountsResponse(**s.status_counts)
        data = {f: getattr(s, f) for f in cls.model_fields if f != "status_counts"}
        return cls(**data, status_counts=counts)
