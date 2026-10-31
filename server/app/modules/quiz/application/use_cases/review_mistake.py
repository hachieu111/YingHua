from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from app.core.ai_policy import AiPolicy
from app.core.clock import Clock
from app.core.glosses import short_meaning
from app.core.single_flight import SingleFlight
from app.modules.auth.application.public import Identity
from app.modules.quiz.application.access import load_wrong_question
from app.modules.quiz.application.dto import MistakeReviewView
from app.modules.quiz.application.mistake_practice import MistakePracticeBuilder
from app.modules.quiz.application.mistake_review_checker import MistakeReviewChecker
from app.modules.quiz.application.ports import (
    LearnerProfileSource,
    MistakeReviewGenerator,
    MistakeReviewRequest,
    QuizUnitOfWork,
    TermFactsSource,
)
from app.modules.quiz.domain.entities import MistakeReview, QuestionOrigin, QuizQuestion, QuizWord
from app.modules.quiz.domain.errors import QuizGeneratorUnavailableError
from app.modules.quiz.domain.mistake_review import chosen_for_llm
from app.modules.review.application.public import local_day_bounds

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MistakeReviewConfig:
    llm_timeout_seconds: float


class ReviewMistakeUseCase:
    """F09.10 — "Vì sao sai?": giải thích câu làm sai và một câu luyện thêm cùng từ (US-NH-79).

    Chỉ cho câu SAI của bài ĐÃ NỘP thuộc chính người dùng (bài người khác → 404). Câu đã có `mistake_review`
    thì
    trả ngay, không gọi lại LLM. Chưa có: LLM bật và người học chưa hết hạn mức giải thích lỗi trong ngày
    (hạn mức RIÊNG, không chung với hạn mức đề LLM) thì gọi LLM NGOÀI giao dịch CSDL, chỉ gửi từ,
    pinyin, nghĩa,
    cấp HSK, hai lựa chọn liên quan và trình độ (một con số). Kết quả LLM phải qua `MistakeReviewChecker`;
    LLM tắt/lỗi/quá thời gian/hết hạn mức/kết quả không hợp lệ → bản dự phòng (giải thích có sẵn của câu +
    câu luyện từ câu ví dụ trong từ điển, nếu có), KHÔNG báo lỗi kỹ thuật. Mọi kết quả được lưu vào câu hỏi.
    Không đổi điểm, thẻ FSRS hay lượt ôn.
    """

    def __init__(
        self,
        uow_factory: Callable[[], QuizUnitOfWork],
        facts: TermFactsSource,
        profiles: LearnerProfileSource,
        generator: MistakeReviewGenerator,
        checker: MistakeReviewChecker,
        practice: MistakePracticeBuilder,
        policy: AiPolicy,
        flight: SingleFlight,
        clock: Clock,
        config: MistakeReviewConfig,
    ) -> None:
        self._uow_factory = uow_factory
        self._facts = facts
        self._profiles = profiles
        self._generator = generator
        self._checker = checker
        self._practice = practice
        self._policy = policy
        self._flight = flight
        self._clock = clock
        self._config = config

    async def execute(self, identity: Identity, quiz_id: int, question_id: int) -> MistakeReviewView:
        async with self._uow_factory() as uow:
            question = await load_wrong_question(uow, identity.user_id, quiz_id, question_id)
        if question.mistake_review is not None:
            return MistakeReviewView(question.id, question.term, question.mistake_review, cached=True)
        # Hai yêu cầu đồng thời cho cùng một câu chỉ gọi LLM một lần.
        review = await self._flight.run(
            f"mistake-review:{question.id}", lambda: self._create(identity.user_id, quiz_id, question)
        )
        return MistakeReviewView(question.id, question.term, review, cached=False)

    async def _create(self, user_id: int, quiz_id: int, question: QuizQuestion) -> MistakeReview:
        word = await self._facts.facts(question.term) or QuizWord(0, question.term, None, None, None, "")
        profile = await self._profiles.profile_of(user_id)
        review = None
        if await self._may_call_llm(user_id, profile.timezone):
            review = await self._from_llm(question, word, profile.hsk_level)
        if review is None:
            review = await self._fallback(question, word, profile.hsk_level)
        async with self._uow_factory() as uow:
            stored = await uow.quizzes.save_mistake_review(quiz_id, question.id, review, self._clock.now())
            await uow.commit()
        return stored

    async def _may_call_llm(self, user_id: int, timezone: str | None) -> bool:
        if not await self._policy.llm_enabled():
            return False
        start, end = local_day_bounds(self._clock.now(), timezone)
        async with self._uow_factory() as uow:
            used = await uow.quizzes.count_llm_mistake_reviews_between(user_id, start, end)
        if used >= await self._policy.daily_limit(user_id):
            logger.warning("Hết hạn mức giải thích lỗi sai trong ngày, dùng nội dung dự phòng")
            return False
        return True

    async def _from_llm(
        self, question: QuizQuestion, word: QuizWord, learner_level: int | None
    ) -> MistakeReview | None:
        request = MistakeReviewRequest(
            word.term,
            word.pinyin,
            short_meaning(word.meaning_vi) or None,
            word.hsk_level,
            chosen_for_llm(question.user_answer),
            question.correct_answer,
            learner_level,
        )
        try:
            payload = await asyncio.wait_for(
                self._generator.generate(request), self._config.llm_timeout_seconds
            )
        except (asyncio.TimeoutError, QuizGeneratorUnavailableError):
            return None
        except Exception:  # lỗi lạ của adapter cũng không được chặn người học xem giải thích
            logger.exception("Lỗi không lường trước khi giải thích lỗi sai bằng LLM")
            return None
        return await self._checker.validate(payload, word, learner_level)

    async def _fallback(
        self, question: QuizQuestion, word: QuizWord, learner_level: int | None
    ) -> MistakeReview:
        logger.warning("Dùng giải thích lỗi sai dự phòng cho câu %s", question.id)
        explanation = question.explanation or f"Đáp án đúng là “{question.correct_answer}”."
        practice = await self._practice.build(word, question, learner_level)
        return MistakeReview(explanation, QuestionOrigin.FALLBACK, None, practice)
