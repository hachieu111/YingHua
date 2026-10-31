from __future__ import annotations

from collections.abc import Callable

from app.core.clock import Clock
from app.core.learning_events import LearningEvent, LearningSource
from app.modules.auth.application.public import Identity
from app.modules.library.application.access import actor_of, load_readable_chapter, require_user
from app.modules.library.application.dto import ProgressInput
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.domain.entities import ReadingProgress
from app.modules.library.domain.errors import InvalidPageNumberError
from app.modules.library.domain.rules import parse_mode
from app.modules.stats.application.public import ActivityDelta


class SaveProgressUseCase:
    """F03.12 — Ghi vị trí dừng của chương và đánh dấu trang đã đọc (US-NH-16, F12.01).

    Chương được coi là đã xong khi người đọc tới trang cuối; đã xong thì giữ nguyên khi đọc lại trang trước.
    Lần đầu đọc một trang thì cộng `pages_read` của ngày, rồi ghi XP (F16.02), cùng giao dịch (F12.01).
    """

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, identity: Identity, chapter_id: int, data: ProgressInput) -> ReadingProgress:
        actor = actor_of(identity)
        user_id = require_user(actor)
        mode = parse_mode(data.mode)
        now = self._clock.now()
        async with self._uow_factory() as uow:
            await load_readable_chapter(uow, chapter_id, actor, now)
            page = await uow.pages.get_by_number(chapter_id, data.page_no)
            if page is None:
                raise InvalidPageNumberError()
            last_no = max(await uow.pages.page_numbers(chapter_id))
            previous = await uow.progress.get(user_id, chapter_id)
            completed = data.completed or data.page_no >= last_no or bool(previous and previous.completed)
            progress = await uow.progress.upsert(user_id, chapter_id, data.page_no, mode, completed, now)
            if await uow.progress.mark_page_read(user_id, page.id, now):
                await uow.activity.record(user_id, now, ActivityDelta(pages_read=1))
                await uow.learning.record(LearningEvent(user_id, LearningSource.PAGE_READ, str(page.id), now))
            await uow.commit()
            await uow.learning.after_commit()
        return progress
