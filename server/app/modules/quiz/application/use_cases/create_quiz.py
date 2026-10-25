from __future__ import annotations

import logging
import random
from collections.abc import Callable
from datetime import datetime

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.quiz.application.access import build_detail
from app.modules.quiz.application.config import QuizConfig
from app.modules.quiz.application.drafting import DraftInput, QuizDrafter
from app.modules.quiz.application.dto import CreateQuizCommand, QuizDetail
from app.modules.quiz.application.ports import (
    LearnerProfile,
    LearnerProfileSource,
    QuizUnitOfWork,
    RelatedCandidateSource,
)
from app.modules.quiz.domain.entities import FallbackReason, NewQuiz, QuizWord, RelatedCandidate
from app.modules.quiz.domain.errors import InvalidQuestionCountError, NotEnoughWordsForQuizError
from app.modules.quiz.domain.examples import RECENT_QUIZZES_FOR_EXAMPLES
from app.modules.quiz.domain.related import pick_related, related_count
from app.modules.quiz.domain.rules import MAX_QUESTION_COUNT, MIN_QUESTION_COUNT, select_words
from app.modules.review.application.public import EstimateRetrievabilityUseCase, local_day_bounds

logger = logging.getLogger(__name__)

DEFAULT_HSK_LEVEL = 3  # cấp chọn nhiễu khi từ và người học đều chưa có cấp HSK


class CreateQuizUseCase:
    """F09.01, F09.06–F09.09 — Tạo bài kiểm tra từ sổ tay (US-NH-45, US-NH-50, US-NH-69, US-LLM-01..03).

    Khoảng 15% số câu (làm tròn nửa lên) là từ mở rộng chưa có trong sổ tay nhưng liên quan tới từ đã lưu
    (F09.09); thiếu ứng viên thì số câu đó được bù bằng từ đã lưu. Từ đã lưu vẫn chọn theo R như dưới đây.

    Chọn từ không ở trạng thái "Bỏ qua" theo R hiện tại (≈60% thấp / 30% trung bình / 10% cao), dưới
    `min_words` từ thì từ chối. LLM tắt hoặc người học hết hạn mức LLM trong ngày thì dùng đề dự phòng ngay.
    Hạn mức F13.05 chỉ đếm bài có `source <> 'fallback'`: đề dự phòng không tốn phí nên không bao giờ bị chặn,
    người học luôn nhận được bài. Việc gọi LLM (tối đa ~20 giây) diễn ra NGOÀI giao dịch CSDL để không giữ
    kết nối trong lúc chờ dịch vụ ngoài.
    """

    def __init__(
        self,
        uow_factory: Callable[[], QuizUnitOfWork],
        profiles: LearnerProfileSource,
        drafter: QuizDrafter,
        related: RelatedCandidateSource,
        estimate: EstimateRetrievabilityUseCase,
        config: QuizConfig,
        clock: Clock,
        rng: random.Random,
    ) -> None:
        self._uow_factory = uow_factory
        self._profiles = profiles
        self._drafter = drafter
        self._related = related
        self._estimate = estimate
        self._config = config
        self._clock = clock
        self._rng = rng

    async def execute(self, identity: Identity, command: CreateQuizCommand) -> QuizDetail:
        user_id = identity.user_id
        count = self._resolve_count(command.question_count)
        now = self._clock.now()
        profile = await self._profiles.profile_of(user_id)
        draft = await self._prepare(user_id, count, profile, now)
        drafted = await self._drafter.draft(draft)
        questions = list(drafted.questions)
        self._rng.shuffle(questions)  # xen kẽ câu từ mở rộng vào giữa các câu từ đã lưu
        async with self._uow_factory() as uow:
            quiz, _ = await uow.quizzes.add(
                NewQuiz(
                    user_id=user_id,
                    source=drafted.source,
                    question_count=len(questions) - drafted.related_count,
                    created_at=now,
                    note=drafted.note,
                    fallback_reason=drafted.fallback_reason,
                    related_count=drafted.related_count,
                ),
                questions,
            )
            await uow.commit()
            return await build_detail(uow, quiz)

    def _resolve_count(self, requested: int | None) -> int:
        count = self._config.question_count if requested is None else requested
        if not MIN_QUESTION_COUNT <= count <= MAX_QUESTION_COUNT:
            raise InvalidQuestionCountError(
                f"Số câu phải từ {MIN_QUESTION_COUNT} đến {MAX_QUESTION_COUNT}",
                details={"min": MIN_QUESTION_COUNT, "max": MAX_QUESTION_COUNT},
            )
        return count

    async def _prepare(self, user_id: int, count: int, profile: LearnerProfile, now: datetime) -> DraftInput:
        async with self._uow_factory() as uow:
            pool = await uow.vocab.quizzable_words(user_id)
            required = self._config.min_words
            if len(pool) < required:
                raise NotEnoughWordsForQuizError(
                    f"Cần tối thiểu {required} từ trong Sổ tay cá nhân",
                    details={"current": len(pool), "required": required},
                )
            retrievability = await self._estimate.execute(uow.cards, user_id, [w.entry_id for w in pool], now)
            related = await self._pick_related(user_id, pool, count, profile)
            words = select_words(
                [(w, retrievability[w.entry_id]) for w in pool], count - len(related), self._rng
            )
            recent = await uow.quizzes.recent_example_ids(user_id, RECENT_QUIZZES_FOR_EXAMPLES)
            contexts = await uow.vocab.contexts(user_id, [w.entry_id for w in words])
            blocked = await self._blocked_reason(uow, user_id, profile, now)
        return DraftInput(
            words=words,
            pool_words=_without(pool, words),
            contexts=contexts,
            default_level=profile.hsk_level or DEFAULT_HSK_LEVEL,
            blocked=blocked,
            related=related,
            learner_level=profile.hsk_level,
            used_example_ids=set(recent),
        )

    async def _pick_related(
        self, user_id: int, pool: list[QuizWord], count: int, profile: LearnerProfile
    ) -> list[RelatedCandidate]:
        """Từ mở rộng cho bài; lỗi khi tìm ứng viên chỉ làm bài không có câu mở rộng, không chặn người học."""
        wanted = related_count(count)
        if wanted == 0:
            return []
        try:
            candidates = await self._related.candidates(user_id, pool, profile.hsk_level)
        except Exception:
            logger.exception("Không lấy được ứng viên từ mở rộng")
            return []
        return pick_related(candidates, wanted, self._rng)

    async def _blocked_reason(
        self, uow: QuizUnitOfWork, user_id: int, profile: LearnerProfile, now: datetime
    ) -> FallbackReason | None:
        if not self._config.llm_enabled:
            return FallbackReason.LLM_DISABLED
        start, end = local_day_bounds(now, profile.timezone)
        used = await uow.quizzes.count_llm_between(user_id, start, end)
        return FallbackReason.DAILY_LIMIT if used >= self._config.daily_llm_limit else None


def _without(pool: list[QuizWord], chosen: list[QuizWord]) -> list[QuizWord]:
    chosen_ids = {w.entry_id for w in chosen}
    return [w for w in pool if w.entry_id not in chosen_ids]
