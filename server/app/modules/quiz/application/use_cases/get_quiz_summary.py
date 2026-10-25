from __future__ import annotations

from collections.abc import Callable

from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.quiz.application.config import QuizConfig
from app.modules.quiz.application.dto import QuizSummary
from app.modules.quiz.application.ports import QuizUnitOfWork


class GetQuizSummaryUseCase:
    """F09.01 — Số từ đủ điều kiện ra đề để giao diện bật/tắt nút "Làm bài kiểm tra" (US-NH-45).

    Từ "Bỏ qua" không tính. Quản trị viên xem được của người khác qua `owner_id` (F13.07).
    """

    def __init__(self, uow_factory: Callable[[], QuizUnitOfWork], config: QuizConfig) -> None:
        self._uow_factory = uow_factory
        self._config = config

    async def execute(self, identity: Identity, owner_id: int | None = None) -> QuizSummary:
        owner = resolve_owner(identity, owner_id)
        async with self._uow_factory() as uow:
            eligible = len(await uow.vocab.quizzable_words(owner))
        return QuizSummary(
            eligible, self._config.min_words, self._config.question_count, self._config.llm_enabled
        )
