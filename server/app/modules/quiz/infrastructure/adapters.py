"""Adapter của M09 với dịch vụ ngoài và module khác: LLM (tắt), nhiễu từ M06, trình độ HSK từ M02."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.auth.application.public import Identity, Role
from app.modules.dictionary.infrastructure.public import SqlDictionaryUnitOfWork
from app.modules.quiz.application.ports import LearnerProfile, QuizGenerationRequest
from app.modules.quiz.domain.entities import DistractorCandidate, FallbackReason
from app.modules.quiz.domain.errors import QuizGeneratorUnavailableError
from app.modules.settings.application.public import GetSettingsUseCase
from app.modules.settings.infrastructure.public import SqlSettingsUnitOfWork


class DisabledQuizGenerator:
    """Hiện thực `QuizGenerator` khi LLM tắt hoặc chưa chọn nhà cung cấp: luôn báo không khả dụng.

    Nhờ vậy luồng sinh đề dự phòng (F09.08) chạy y hệt khi bật LLM thật mà không gọi dịch vụ ngoài nào.
    """

    async def generate(self, request: QuizGenerationRequest) -> object:
        raise QuizGeneratorUnavailableError(FallbackReason.LLM_DISABLED.value, "LLM đang tắt")


class DictionaryDistractorSource:
    """Từ HSK ngẫu nhiên kèm nghĩa từ M06, làm phương án nhiễu cho đề dự phòng."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def sample(self, level: int, limit: int, exclude: Sequence[str]) -> list[DistractorCandidate]:
        async with SqlDictionaryUnitOfWork(self._session_factory) as uow:
            samples = await uow.reader.sample_hsk_words(level, limit, exclude)
        return [DistractorCandidate(s.term, s.meaning_vi, s.pinyin) for s in samples]


class SettingsLearnerProfileSource:
    """Trình độ HSK và múi giờ của người học qua giao diện công khai của M02."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def profile_of(self, user_id: int) -> LearnerProfile:
        identity = Identity(user_id=user_id, role=Role.USER, session_id="")
        use_case = GetSettingsUseCase(lambda: SqlSettingsUnitOfWork(self._session_factory))
        settings = await use_case.execute(identity)
        return LearnerProfile(settings.hsk_level, settings.timezone)
