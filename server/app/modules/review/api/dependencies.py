from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.container import Container, get_container
from app.core.external_call_log import SqlLlmCallLogWriter
from app.modules.admin.api.public import build_ensure_target
from app.modules.admin.application.public import SystemSettingsSnapshot
from app.modules.admin.application.use_cases.get_user_overview import GetUserOverviewUseCase
from app.modules.dictionary.infrastructure.public import JiebaExampleLevelChecker
from app.modules.library.application.public import CountUserContentUseCase, LibraryPageAccess
from app.modules.library.infrastructure.public import SqlLibraryUnitOfWork
from app.modules.review.application.admin_activity import ReviewLibraryActivitySource
from app.modules.review.application.ports import AiNoteGenerator, ReviewUnitOfWork, VocabCardSource
from app.modules.review.application.stats_facts import ReviewLearningFactsSource
from app.modules.review.application.use_cases.get_ai_note import AiNoteConfig, GetAiNoteUseCase
from app.modules.review.application.use_cases.get_card_history import GetCardHistoryUseCase
from app.modules.review.application.use_cases.get_due_cards import GetDueCardsUseCase
from app.modules.review.application.use_cases.get_review_summary import GetReviewSummaryUseCase
from app.modules.review.application.use_cases.grade_card import GradeCardUseCase
from app.modules.review.application.use_cases.list_cards import ListCardsUseCase
from app.modules.review.application.use_cases.reset_card import ResetCardUseCase
from app.modules.review.application.use_cases.resume_card import ResumeCardUseCase
from app.modules.review.application.use_cases.suspend_card import SuspendCardUseCase
from app.modules.review.infrastructure.fsrs_scheduler import FsrsScheduler
from app.modules.review.infrastructure.gemini_ai_note import DisabledAiNoteGenerator, GeminiAiNoteGenerator
from app.modules.review.infrastructure.learner_profile import SettingsLearnerProfileSource
from app.modules.review.infrastructure.timezone_source import SettingsTimezoneSource
from app.modules.review.infrastructure.uow import SqlReviewUnitOfWork
from app.modules.review.infrastructure.word_knowledge import DictionaryWordKnowledge
from app.modules.vocab.infrastructure.public import DictionaryTermAdapter, SqlVocabCardSource


@dataclass(slots=True)
class ReviewServices:
    get_due: GetDueCardsUseCase
    grade: GradeCardUseCase
    suspend: SuspendCardUseCase
    resume: ResumeCardUseCase
    reset: ResetCardUseCase
    history: GetCardHistoryUseCase
    summary: GetReviewSummaryUseCase
    list_cards: ListCardsUseCase
    overview: GetUserOverviewUseCase
    ai_note: GetAiNoteUseCase


def build_ai_note_generator(container: Container) -> AiNoteGenerator:
    """Gemini khi có khóa API và nhà cung cấp là gemini; không thì adapter "tắt" (luôn dùng nội dung dự
    phòng). Công tắc `llm_enabled` do quản trị đặt (F13.05) được use case kiểm trước. Khóa chỉ đọc từ
    cấu hình."""
    settings = container.settings
    key = settings.llm_api_key
    if key is not None and key.get_secret_value() and settings.llm_provider == "gemini":
        return GeminiAiNoteGenerator(
            key,
            settings.llm_model,
            settings.llm_timeout_seconds,
            SqlLlmCallLogWriter(container.session_factory).record,
            thinking_level=settings.llm_thinking_level,
        )
    return DisabledAiNoteGenerator()


def build_ai_note_use_case(
    container: Container, uow_factory: Callable[[], ReviewUnitOfWork], system: SystemSettingsSnapshot
) -> GetAiNoteUseCase:
    settings = container.settings
    factory = container.session_factory
    return GetAiNoteUseCase(
        uow_factory,
        build_ai_note_generator(container),
        DictionaryWordKnowledge(factory),
        JiebaExampleLevelChecker(factory),
        SettingsLearnerProfileSource(factory),
        container.single_flight,
        AiNoteConfig(
            llm_enabled=system.llm_enabled,
            daily_limit=system.ai_note_daily_limit,
            regenerate_limit=settings.ai_note_regenerate_limit,
            llm_timeout_seconds=settings.llm_timeout_seconds,
            model=settings.llm_model,
        ),
        container.clock,
    )


def build_review_services(container: Container, system: SystemSettingsSnapshot) -> ReviewServices:
    """Lắp ghép M08. Nội dung thẻ và bộ thẻ do M07 hiện thực qua port `VocabCardSource` (chung phiên)."""
    clock = container.clock
    pages = LibraryPageAccess(lambda: SqlLibraryUnitOfWork(container.session_factory), clock)
    dictionary = DictionaryTermAdapter(container.session_factory)

    def vocab_source(session: AsyncSession) -> VocabCardSource:
        return SqlVocabCardSource(session, dictionary, pages)

    def uow_factory() -> ReviewUnitOfWork:
        return SqlReviewUnitOfWork(container.session_factory, vocab_source)

    scheduler = FsrsScheduler()
    summary = GetReviewSummaryUseCase(uow_factory, SettingsTimezoneSource(container.session_factory), clock)
    content = CountUserContentUseCase(lambda: SqlLibraryUnitOfWork(container.session_factory))
    activity = ReviewLibraryActivitySource(summary, content, uow_factory)
    overview = GetUserOverviewUseCase(build_ensure_target(container), activity)
    return ReviewServices(
        get_due=GetDueCardsUseCase(uow_factory, clock),
        grade=GradeCardUseCase(
            uow_factory, scheduler, clock, SettingsTimezoneSource(container.session_factory)
        ),
        suspend=SuspendCardUseCase(uow_factory, clock),
        resume=ResumeCardUseCase(uow_factory, clock),
        reset=ResetCardUseCase(uow_factory, scheduler, clock),
        history=GetCardHistoryUseCase(uow_factory),
        summary=summary,
        list_cards=ListCardsUseCase(uow_factory, clock),
        overview=overview,
        ai_note=build_ai_note_use_case(container, uow_factory, system),
    )


def build_learning_facts_source(container: Container) -> ReviewLearningFactsSource:
    """Số liệu học tập cho thống kê cá nhân (F12.01): lắp từ tổng kết ôn tập của chính M08."""
    pages = LibraryPageAccess(lambda: SqlLibraryUnitOfWork(container.session_factory), container.clock)
    dictionary = DictionaryTermAdapter(container.session_factory)

    def vocab_source(session: AsyncSession) -> VocabCardSource:
        return SqlVocabCardSource(session, dictionary, pages)

    def uow_factory() -> ReviewUnitOfWork:
        return SqlReviewUnitOfWork(container.session_factory, vocab_source)

    summary = GetReviewSummaryUseCase(
        uow_factory, SettingsTimezoneSource(container.session_factory), container.clock
    )
    return ReviewLearningFactsSource(summary, uow_factory)


async def get_review_services(container: Container = Depends(get_container)) -> ReviewServices:
    """Công tắc LLM và hạn mức Thẻ mở rộng AI đọc từ cấu hình hệ thống mỗi yêu cầu (F13.05)."""
    return build_review_services(container, await container.system_settings.snapshot())
