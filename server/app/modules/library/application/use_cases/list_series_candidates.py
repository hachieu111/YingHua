from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.library.application.access import actor_of, attach_progress, require_user
from app.modules.library.application.dto import SeriesCandidate
from app.modules.library.application.ports import LibraryUnitOfWork, SeriesFilter

CANDIDATE_LIMIT = 200  # đủ rộng để M10 xếp hạng; không trả toàn bộ thư viện công khai


class ListSeriesCandidatesUseCase:
    """F10.04 (phần dữ liệu của M03) — Truyện công khai có cấp HSK ước tính trong [hsk_min, hsk_max].

    Kèm trạng thái riêng của người gọi (đã thêm vào Thư viện, đã đọc xong) và độ phổ biến, để M10 tự xếp
    hạng. Chỉ truyện công khai có ít nhất một chương; không bao giờ trả truyện riêng tư của người khác.
    """

    def __init__(self, uow_factory: Callable[[], LibraryUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, identity: Identity, hsk_min: int, hsk_max: int) -> list[SeriesCandidate]:
        actor = actor_of(identity)
        require_user(actor)
        flt = SeriesFilter(viewer_id=actor.user_id, scope="public", hsk_min=hsk_min, hsk_max=hsk_max)
        async with self._uow_factory() as uow:
            views, _ = await uow.series.search(flt, 0, CANDIDATE_LIMIT)
            views = await attach_progress(uow, views, actor.user_id)
            counts = await uow.series.library_counts([v.series.id for v in views])
        return [
            SeriesCandidate(
                view,
                counts.get(view.series.id, 0),
                view.progress is not None
                and view.progress.pages_total > 0
                and view.progress.pages_read >= view.progress.pages_total,
            )
            for view in views
        ]
