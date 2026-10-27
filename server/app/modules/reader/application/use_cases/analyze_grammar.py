from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.core.ai_policy import AiPolicy
from app.core.clock import Clock
from app.core.single_flight import SingleFlight
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.reader.application.access import load_readable_bubble
from app.modules.reader.application.dto import GrammarView
from app.modules.reader.application.ports import (
    GrammarAnalyzer,
    GrammarRequest,
    LearnerTimezoneSource,
    ReaderUnitOfWork,
    SentenceLevelChecker,
)
from app.modules.reader.domain.errors import (
    BubbleHasNoHanError,
    GrammarAnalyzerUnavailableError,
    SentenceTooLongError,
)
from app.modules.reader.domain.grammar import (
    EXAMPLE_MAX_HSK_LEVEL,
    MAX_SENTENCE_CHARS,
    MAX_TRANSLATION_CHARS,
    GrammarContent,
    GrammarPoint,
    GrammarStatus,
    has_han,
    normalize_sentence,
    parse_points,
    parse_tree,
    sentence_hash,
)
from app.modules.review.application.public import local_day_bounds

logger = logging.getLogger(__name__)

_UNAVAILABLE: Any = object()  # dấu hiệu nội bộ: LLM không trả được kết quả (khác với JSON hỏng = None)


@dataclass(frozen=True, slots=True)
class GrammarConfig:
    llm_timeout_seconds: float
    model: str | None = None  # tên mô hình ghi kèm kết quả đã lưu


class AnalyzeGrammarUseCase:
    """F05.09 — Phân tích ngữ pháp câu thoại của một bong bóng (US-NH-78).

    Kiểm quyền đọc bong bóng (F03.10), chuẩn hóa câu rồi tra bộ nhớ dùng chung theo SHA-256: có kết quả thì
    trả ngay, không gọi LLM và không tốn hạn mức. Chưa có: LLM tắt hoặc người học hết hạn mức ngày thì trả
    trạng thái `unavailable` / `limit_reached` (không phải lỗi kỹ thuật); còn lại gọi LLM NGOÀI giao dịch CSDL
    (tối đa ~20 giây), kiểm kết quả ở máy chủ (`domain.grammar`) và độ khó của ví dụ, lưu phần hợp lệ và ghi
    một lượt yêu cầu của người học. Không còn phần nào hợp lệ → `unanalyzable`, không lưu cache (vẫn tính
    lượt vì LLM đã trả lời). LLM lỗi kỹ thuật (mạng, timeout, 5xx, 429) → `unavailable`, KHÔNG tính lượt.

    Hai yêu cầu đồng thời cho cùng một câu chỉ gọi LLM một lần; chỉ người gọi thật sự bị tính lượt.
    """

    def __init__(
        self,
        uow_factory: Callable[[], ReaderUnitOfWork],
        pages: PageAccessPort,
        analyzer: GrammarAnalyzer,
        levels: SentenceLevelChecker,
        timezones: LearnerTimezoneSource,
        policy: AiPolicy,
        flight: SingleFlight,
        clock: Clock,
        config: GrammarConfig,
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._analyzer = analyzer
        self._levels = levels
        self._timezones = timezones
        self._policy = policy
        self._flight = flight
        self._clock = clock
        self._config = config

    async def execute(self, identity: Identity, bubble_id: int) -> GrammarView:
        user_id = identity.user_id
        async with self._uow_factory() as uow:
            bubble = await load_readable_bubble(uow, self._pages, identity, bubble_id)
            sentence = normalize_sentence(bubble.text_zh)
            if not has_han(sentence):
                raise BubbleHasNoHanError()
            if len(sentence) > MAX_SENTENCE_CHARS:
                raise SentenceTooLongError(details={"max_chars": MAX_SENTENCE_CHARS})
            digest = sentence_hash(sentence)
            cached = await uow.grammar.get_by_hash(digest)
            if cached is not None:
                return GrammarView(GrammarStatus.OK, bubble_id, sentence, cached.content, cached=True)
            translation = (bubble.text_vi or "")[:MAX_TRANSLATION_CHARS] or None
        blocked = await self._blocked(user_id)
        if blocked is not None:
            return GrammarView(blocked, bubble_id, sentence)
        return await self._flight.run(
            f"grammar:{digest}", lambda: self._analyze(user_id, bubble_id, digest, sentence, translation)
        )

    async def _blocked(self, user_id: int) -> GrammarStatus | None:
        if not await self._policy.llm_enabled():
            return GrammarStatus.UNAVAILABLE
        start, end = local_day_bounds(self._clock.now(), await self._timezones.timezone_of(user_id))
        async with self._uow_factory() as uow:
            used = await uow.grammar.count_requests_between(user_id, start, end)
        if used >= await self._policy.daily_limit():
            logger.warning("Hết hạn mức phân tích ngữ pháp trong ngày")
            return GrammarStatus.LIMIT_REACHED
        return None

    async def _analyze(
        self, user_id: int, bubble_id: int, digest: str, sentence: str, translation: str | None
    ) -> GrammarView:
        payload = await self._ask(GrammarRequest(sentence, translation))
        if payload is _UNAVAILABLE:
            # Lỗi kỹ thuật phía LLM (mạng, timeout, 5xx, 429) không phải lỗi của người học: không tính lượt.
            return GrammarView(GrammarStatus.UNAVAILABLE, bubble_id, sentence)
        content = await self._validated(payload, sentence)
        async with self._uow_factory() as uow:
            analysis = None
            if content is not None:
                analysis = await uow.grammar.add(digest, sentence, content, self._config.model)
            await uow.grammar.add_request(user_id, analysis.id if analysis else None, self._clock.now())
            await uow.commit()
        if analysis is None:
            logger.warning("Kết quả phân tích ngữ pháp không còn phần nào hợp lệ")
            return GrammarView(GrammarStatus.UNANALYZABLE, bubble_id, sentence)
        return GrammarView(GrammarStatus.OK, bubble_id, sentence, analysis.content)

    async def _ask(self, request: GrammarRequest) -> object:
        try:
            return await asyncio.wait_for(self._analyzer.analyze(request), self._config.llm_timeout_seconds)
        except (asyncio.TimeoutError, GrammarAnalyzerUnavailableError):
            return _UNAVAILABLE
        except Exception:  # lỗi lạ của adapter cũng không được làm hỏng trang đọc
            logger.exception("Lỗi không lường trước khi phân tích ngữ pháp bằng LLM")
            return _UNAVAILABLE

    async def _validated(self, payload: object, sentence: str) -> GrammarContent | None:
        if not isinstance(payload, dict):
            return None
        tree = parse_tree(payload.get("tree"), sentence)
        points = await self._within_level(parse_points(payload.get("points")))
        content = GrammarContent(tree, tuple(points))
        return None if content.is_empty else content

    async def _within_level(self, points: list[GrammarPoint]) -> list[GrammarPoint]:
        """Ví dụ phải đủ dễ (HSK ≤ `EXAMPLE_MAX_HSK_LEVEL`); câu không đo được độ khó cũng bị loại."""
        if not points:
            return []
        levels = await self._levels.difficulties([p.example_zh for p in points])
        return [
            p
            for p, level in zip(points, levels, strict=True)
            if level is not None and level <= EXAMPLE_MAX_HSK_LEVEL
        ]
