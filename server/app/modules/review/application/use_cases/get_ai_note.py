from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from app.core.clock import Clock
from app.core.single_flight import SingleFlight
from app.modules.auth.application.public import Identity
from app.modules.review.application.dto import AiNoteRequest, AiNoteView, EntryFace
from app.modules.review.application.ports import (
    AiNoteGenerator,
    LearnerProfileSource,
    ReviewUnitOfWork,
    SentenceLevelChecker,
    WordKnowledge,
)
from app.modules.review.domain.ai_note import (
    EXAMPLE_COUNT,
    PHRASE_MAX,
    PHRASE_MIN,
    AiExample,
    AiNote,
    AiNoteContent,
    AiNoteSource,
    CharParts,
    allowed_mnemonic_chars,
    build_mnemonic,
    example_difficulty_cap,
    examples_within_level,
    merge_examples,
    parse_llm_examples,
    parse_llm_phrases,
    sanitize_mnemonic,
)
from app.modules.review.domain.errors import (
    AiNoteEntryNotFoundError,
    AiNoteGeneratorUnavailableError,
    AiNoteRegenerateLimitError,
)
from app.modules.review.domain.rules import local_day_bounds

logger = logging.getLogger(__name__)

EXAMPLE_FETCH_LIMIT = 6  # lấy dư câu ví dụ dự phòng để chọn đủ 2 câu


@dataclass(frozen=True, slots=True)
class AiNoteConfig:
    llm_enabled: bool
    daily_limit: int  # số lần gọi LLM tạo thẻ mỗi người mỗi ngày
    regenerate_limit: int  # số lần "Tạo lại" cho mỗi mục từ
    llm_timeout_seconds: float
    model: str | None = None  # tên mô hình ghi vào bộ đệm khi nội dung do LLM sinh


@dataclass(frozen=True, slots=True)
class _Produced:
    content: AiNoteContent
    source: AiNoteSource


class GetAiNoteUseCase:
    """F08.11 — Thẻ mở rộng AI của mục từ: 2 câu ví dụ, mẹo chiết tự, 2–3 cụm đi kèm (US-NH-75).

    Có trong bộ đệm (`vocab_ai_notes`) và không yêu cầu tạo lại thì trả ngay, không gọi LLM. Chưa có (hoặc tạo
    lại): nếu LLM bật và chưa hết hạn mức ngày thì gọi LLM (chỉ gửi từ, pinyin, nghĩa, cấp HSK, trình độ và dữ
    liệu chiết tự của từ điển), kiểm kết quả như F09.07: đúng lược đồ, mỗi ví dụ chứa đúng từ và có độ khó
    ≤ trình độ+1, mẹo chiết tự chỉ nhắc chữ/thành phần có trong dữ liệu M06 (sai thì dùng bản dựng từ dữ
    liệu). LLM tắt/lỗi/quá thời gian/hết hạn mức/kết quả không dùng được → nội dung dự phòng từ M06
    (`fallback`), KHÔNG báo lỗi kỹ thuật. Tạo lại bị giới hạn `regenerate_limit` lần cho mỗi mục từ (vượt →
    429). Mục từ của người khác → 404. Nội dung chỉ để học, không đổi lịch ôn, trạng thái hay ghi chú.
    """

    def __init__(
        self,
        uow_factory: Callable[[], ReviewUnitOfWork],
        generator: AiNoteGenerator,
        knowledge: WordKnowledge,
        levels: SentenceLevelChecker,
        profiles: LearnerProfileSource,
        flight: SingleFlight,
        config: AiNoteConfig,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._generator = generator
        self._knowledge = knowledge
        self._levels = levels
        self._profiles = profiles
        self._flight = flight
        self._config = config
        self._clock = clock

    async def execute(self, identity: Identity, entry_id: int, *, regenerate: bool = False) -> AiNoteView:
        user_id = identity.user_id
        async with self._uow_factory() as uow:
            face = (await uow.vocab.faces(user_id, [entry_id])).get(entry_id)
            if face is None:
                raise AiNoteEntryNotFoundError()
            cached = await uow.ai_notes.get(entry_id)
            if cached is not None and not regenerate:
                return self._view(cached)
            if regenerate and cached is not None and cached.regenerate_count >= self._config.regenerate_limit:
                raise AiNoteRegenerateLimitError(details={"limit": self._config.regenerate_limit})
        # Hai yêu cầu đồng thời cùng một từ chỉ gọi LLM một lần.
        key = f"ai-note:{user_id}:{entry_id}:{int(regenerate)}"
        return await self._flight.run(key, lambda: self._create(user_id, face, cached, regenerate))

    async def _create(
        self, user_id: int, face: EntryFace, cached: AiNote | None, regenerate: bool
    ) -> AiNoteView:
        level, timezone = await self._profiles.profile_of(user_id)
        parts = await self._knowledge.char_parts(face.term)
        cap = example_difficulty_cap(level, face.hsk_level)
        fallback = await self._fallback(face.term, parts, cap)
        produced = None
        if await self._may_call_llm(user_id, timezone):
            produced = await self._from_llm(face, level, parts, cap, fallback)
        if produced is None:
            logger.warning("Thẻ mở rộng AI dùng nội dung dự phòng cho mục từ %s", face.vocab_entry_id)
            produced = _Produced(fallback, AiNoteSource.FALLBACK)
        count = cached.regenerate_count + 1 if regenerate and cached is not None else 0
        is_llm = produced.source is AiNoteSource.LLM
        note = AiNote(
            vocab_entry_id=face.vocab_entry_id,
            content=produced.content,
            source=produced.source,
            generated_at=self._clock.now(),
            regenerate_count=count,
            model=self._config.model if is_llm else None,
        )
        async with self._uow_factory() as uow:
            await uow.ai_notes.save(note)
            await uow.commit()
        return self._view(note)

    async def _may_call_llm(self, user_id: int, timezone: str | None) -> bool:
        if not self._config.llm_enabled:
            return False
        start, end = local_day_bounds(self._clock.now(), timezone)
        async with self._uow_factory() as uow:
            used = await uow.ai_notes.count_llm_between(user_id, start, end)
        if used >= self._config.daily_limit:
            logger.warning("Hết hạn mức Thẻ mở rộng AI trong ngày, dùng nội dung dự phòng")
            return False
        return True

    async def _fallback(self, term: str, parts: list[CharParts], cap: int) -> AiNoteContent:
        examples = await self._knowledge.examples(term, cap, EXAMPLE_FETCH_LIMIT)
        phrases = await self._knowledge.collocations(term, PHRASE_MAX)
        return AiNoteContent(tuple(examples[:EXAMPLE_COUNT]), build_mnemonic(parts), tuple(phrases))

    async def _from_llm(
        self, face: EntryFace, level: int | None, parts: list[CharParts], cap: int, fallback: AiNoteContent
    ) -> _Produced | None:
        request = AiNoteRequest(face.term, face.pinyin, face.meaning_vi, face.hsk_level, level, tuple(parts))
        try:
            payload = await asyncio.wait_for(
                self._generator.generate(request), self._config.llm_timeout_seconds
            )
        except (asyncio.TimeoutError, AiNoteGeneratorUnavailableError):
            return None
        except Exception:  # lỗi lạ của adapter cũng không được chặn người học nhận thẻ
            logger.exception("Lỗi không lường trước khi sinh Thẻ mở rộng AI")
            return None
        return await self._validated(payload, face.term, parts, cap, fallback)

    async def _validated(
        self, payload: object, term: str, parts: list[CharParts], cap: int, fallback: AiNoteContent
    ) -> _Produced | None:
        candidates = parse_llm_examples(payload, term)
        levels = await self._levels.difficulties([e.zh for e in candidates]) if candidates else []
        valid = examples_within_level(candidates, levels, cap)
        phrases = parse_llm_phrases(payload, term)
        if not valid:
            return None  # không có câu ví dụ nào dùng được: coi như kết quả không hợp lệ
        for extra in fallback.phrases:  # thiếu cụm từ thì bù từ dữ liệu từ điển
            if len(phrases) >= PHRASE_MIN:
                break
            if all(extra.zh != p.zh for p in phrases):
                phrases.append(extra)
        raw_mnemonic = payload.get("mnemonic") if isinstance(payload, dict) else None
        mnemonic = sanitize_mnemonic(raw_mnemonic, allowed_mnemonic_chars(term, parts), fallback.mnemonic)
        examples: list[AiExample] = merge_examples(valid, fallback.examples)
        return _Produced(AiNoteContent(tuple(examples), mnemonic, tuple(phrases)), AiNoteSource.LLM)

    def _view(self, note: AiNote) -> AiNoteView:
        return AiNoteView(note, self._config.regenerate_limit)
