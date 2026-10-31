from __future__ import annotations

import random
from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.container import Container, get_container
from app.core.external_call_log import SqlLlmCallLogWriter
from app.modules.dictionary.infrastructure.public import JiebaExampleLevelChecker
from app.modules.quiz.application.config import QuizConfig
from app.modules.quiz.application.drafting import FallbackQuestionBuilder, QuizDrafter
from app.modules.quiz.application.llm_review import LlmReviewer
from app.modules.quiz.application.mistake_practice import MistakePracticeBuilder
from app.modules.quiz.application.mistake_review_checker import MistakeReviewChecker
from app.modules.quiz.application.ports import (
    MistakeReviewGenerator,
    QuizGenerator,
    QuizUnitOfWork,
    QuizVocabSource,
)
from app.modules.quiz.application.use_cases.answer_mistake_practice import AnswerMistakePracticeUseCase
from app.modules.quiz.application.use_cases.create_quiz import CreateQuizUseCase
from app.modules.quiz.application.use_cases.delete_quiz import DeleteQuizUseCase
from app.modules.quiz.application.use_cases.get_quiz import GetQuizUseCase
from app.modules.quiz.application.use_cases.get_quiz_summary import GetQuizSummaryUseCase
from app.modules.quiz.application.use_cases.list_quizzes import ListQuizzesUseCase
from app.modules.quiz.application.use_cases.review_mistake import MistakeReviewConfig, ReviewMistakeUseCase
from app.modules.quiz.application.use_cases.save_quiz_word import SaveQuizWordUseCase
from app.modules.quiz.application.use_cases.submit_quiz import SubmitQuizUseCase
from app.modules.quiz.infrastructure.adapters import (
    DictionaryDistractorSource,
    DisabledQuizGenerator,
    SettingsLearnerProfileSource,
)
from app.modules.quiz.infrastructure.call_log import SqlLlmCallLog
from app.modules.quiz.infrastructure.examples import DictionaryExampleSource
from app.modules.quiz.infrastructure.gemini import GeminiQuizGenerator
from app.modules.quiz.infrastructure.gemini_mistake import (
    DisabledMistakeReviewGenerator,
    GeminiMistakeReviewGenerator,
)
from app.modules.quiz.infrastructure.related import RelatedCandidateAdapter
from app.modules.quiz.infrastructure.term_facts import DictionaryTermFacts
from app.modules.quiz.infrastructure.uow import SqlQuizUnitOfWork
from app.modules.review.application.public import EstimateRetrievabilityUseCase, RescheduleCardsNowUseCase
from app.modules.review.infrastructure.public import FsrsScheduler
from app.modules.vocab.api.public import build_vocab_services
from app.modules.vocab.infrastructure.public import SqlVocabQuizSource


@dataclass(slots=True)
class QuizServices:
    summary: GetQuizSummaryUseCase
    create: CreateQuizUseCase
    list_quizzes: ListQuizzesUseCase
    get: GetQuizUseCase
    submit: SubmitQuizUseCase
    delete: DeleteQuizUseCase
    save_word: SaveQuizWordUseCase
    review_mistake: ReviewMistakeUseCase
    answer_practice: AnswerMistakePracticeUseCase


def build_generator(container: Container) -> QuizGenerator:
    """Chọn adapter sinh đề: Gemini khi có khóa API và nhà cung cấp là gemini; không thì adapter "tắt" (luôn
    dùng đề dự phòng). Công tắc `llm_enabled` do quản trị đặt (F13.05) nằm ở `QuizConfig`/`AiPolicy`, use case
    kiểm trước khi gọi. Khóa chỉ đọc từ cấu hình, không bao giờ log."""
    settings = container.settings
    key = settings.llm_api_key
    if key is not None and key.get_secret_value() and settings.llm_provider == "gemini":
        return GeminiQuizGenerator(
            key,
            settings.llm_model,
            settings.llm_timeout_seconds,
            SqlLlmCallLog(container.session_factory),
            thinking_level=settings.llm_thinking_level,
        )
    return DisabledQuizGenerator()


def build_quiz_services(container: Container) -> QuizServices:
    settings, clock = container.settings, container.clock

    def vocab_source(session: AsyncSession) -> QuizVocabSource:
        return SqlVocabQuizSource(session)

    def uow_factory() -> QuizUnitOfWork:
        return SqlQuizUnitOfWork(container.session_factory, vocab_source, examples)

    examples = DictionaryExampleSource(container.session_factory)
    config = QuizConfig(question_count=settings.quiz_question_count, min_words=settings.quiz_min_words)
    policies = container.ai_policies
    rng = random.Random()
    drafter = QuizDrafter(
        build_generator(container),
        FallbackQuestionBuilder(DictionaryDistractorSource(container.session_factory), examples, rng),
        settings.llm_timeout_seconds,
        LlmReviewer(JiebaExampleLevelChecker(container.session_factory), examples, rng),
    )
    return QuizServices(
        summary=GetQuizSummaryUseCase(uow_factory, config, policies.quiz),
        create=CreateQuizUseCase(
            uow_factory,
            SettingsLearnerProfileSource(container.session_factory),
            drafter,
            RelatedCandidateAdapter(container.session_factory),
            EstimateRetrievabilityUseCase(FsrsScheduler()),
            config,
            policies.quiz,
            clock,
            rng,
        ),
        list_quizzes=ListQuizzesUseCase(uow_factory),
        get=GetQuizUseCase(uow_factory),
        submit=SubmitQuizUseCase(uow_factory, RescheduleCardsNowUseCase(), clock),
        delete=DeleteQuizUseCase(uow_factory, clock),
        save_word=SaveQuizWordUseCase(uow_factory, build_vocab_services(container).save_word),
        review_mistake=ReviewMistakeUseCase(
            uow_factory,
            DictionaryTermFacts(container.session_factory),
            SettingsLearnerProfileSource(container.session_factory),
            build_mistake_generator(container),
            MistakeReviewChecker(JiebaExampleLevelChecker(container.session_factory)),
            MistakePracticeBuilder(
                FallbackQuestionBuilder(DictionaryDistractorSource(container.session_factory), examples, rng)
            ),
            policies.mistake_review,
            container.single_flight,
            clock,
            MistakeReviewConfig(settings.llm_timeout_seconds),
        ),
        answer_practice=AnswerMistakePracticeUseCase(uow_factory),
    )


def build_mistake_generator(container: Container) -> MistakeReviewGenerator:
    """Gemini khi có khóa API và nhà cung cấp là gemini; không thì adapter "tắt" (luôn dùng bản dự phòng).
    Công tắc `llm_enabled` do quản trị đặt (F13.05) được use case kiểm trước. Khóa chỉ đọc từ cấu hình."""
    settings = container.settings
    key = settings.llm_api_key
    if key is not None and key.get_secret_value() and settings.llm_provider == "gemini":
        return GeminiMistakeReviewGenerator(
            key,
            settings.llm_model,
            settings.llm_timeout_seconds,
            SqlLlmCallLogWriter(container.session_factory).record,
            thinking_level=settings.llm_thinking_level,
        )
    return DisabledMistakeReviewGenerator()


def get_quiz_services(container: Container = Depends(get_container)) -> QuizServices:
    """Công tắc LLM và hạn mức đề đọc từ chính sách AI (cấu hình F13.05, nâng khi VIP F17.04) mỗi yêu cầu."""
    return build_quiz_services(container)
