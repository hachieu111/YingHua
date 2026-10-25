from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.modules.admin.application.public import record_admin_action, resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.quiz.application.access import load_quiz
from app.modules.quiz.application.ports import QuizUnitOfWork


class DeleteQuizUseCase:
    """F13.07 — Quản trị viên xóa một bài kiểm tra của người dùng (kéo theo câu hỏi nhờ ON DELETE CASCADE).

    Người dùng thường không có đường xóa bài; xóa bài của người khác ghi nhật ký `quiz.delete` (F13.06).
    """

    def __init__(self, uow_factory: Callable[[], QuizUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, quiz_id: int, owner_id: int | None = None) -> None:
        owner = resolve_owner(identity, owner_id)
        async with self._uow_factory() as uow:
            quiz = await load_quiz(uow, owner, quiz_id)
            await uow.quizzes.delete(owner, quiz.id)
            await record_admin_action(
                uow.audit, identity, owner, "quiz.delete", "quiz", quiz.id, self._clock.now()
            )
            await uow.commit()
