from __future__ import annotations

from collections.abc import Callable

from app.modules.admin.application.public import resolve_owner
from app.modules.auth.application.public import Identity
from app.modules.quiz.application.dto import QuizPage
from app.modules.quiz.application.ports import QuizUnitOfWork


class ListQuizzesUseCase:
    """F09.05 — Lịch sử bài kiểm tra của người học, mới nhất trước (US-NH-49).

    Gồm cả bài đang làm dở. Quản trị viên xem được của người khác qua `owner_id` (F13.07).
    """

    def __init__(self, uow_factory: Callable[[], QuizUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(
        self, identity: Identity, page: int, size: int, owner_id: int | None = None
    ) -> QuizPage:
        owner = resolve_owner(identity, owner_id)
        async with self._uow_factory() as uow:
            items, total = await uow.quizzes.page(owner, (page - 1) * size, size)
        return QuizPage(items, total)
