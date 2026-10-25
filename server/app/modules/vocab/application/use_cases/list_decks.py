from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.library.application.public import PageAccessPort
from app.modules.review.application.public import DeckKind, EntrySrsSummary
from app.modules.vocab.application.dto import DeckList, DeckSummary
from app.modules.vocab.application.ports import VocabUnitOfWork
from app.modules.vocab.domain.entities import VocabStatus

STARRED_DECK_TITLE = "Từ đánh dấu sao"


class ListDecksUseCase:
    """F07.07, F08.01 — Bộ thẻ cho màn Flashcard: một bộ theo mỗi truyện có từ đã lưu và bộ "Từ đánh dấu sao".

    Từ thuộc truyện qua ngữ cảnh (ngữ cảnh -> trang -> chương -> truyện); từ gặp ở nhiều truyện thuộc nhiều
    bộ. Chỉ tính truyện người gọi còn đọc được. `reviewed_count`: số từ đã ôn ít nhất một lượt; `due_count`:
    số thẻ đang đến hạn của các từ còn "Đang học". Khóa bộ (`key`) dùng làm tham số `deck` của /cards/due.
    """

    def __init__(
        self, uow_factory: Callable[[], VocabUnitOfWork], pages: PageAccessPort, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._pages = pages
        self._clock = clock

    async def execute(self, identity: Identity) -> DeckList:
        user_id = identity.user_id
        now = self._clock.now()
        async with self._uow_factory() as uow:
            links = await uow.contexts.page_links(user_id)
            series_of = await self._pages.series_of_pages(identity, sorted({p for _, p in links}))
            titles: dict[int, str] = {}
            by_series: dict[int, set[int]] = defaultdict(set)
            for entry_id, page_id in links:
                ref = series_of.get(page_id)
                if ref is not None:
                    titles[ref.series_id] = ref.title
                    by_series[ref.series_id].add(entry_id)
            starred = set(await uow.entries.starred_ids(user_id))
            all_ids = sorted(starred.union(*by_series.values()))
            entries = await uow.entries.get_many(user_id, all_ids)
            srs = await uow.cards.summaries_for_entries(user_id, all_ids, now)
        learning = {i for i, e in entries.items() if e.status is VocabStatus.LEARNING}
        items = [
            _summarize(
                DeckKind.STARRED.value, DeckKind.STARRED, None, STARRED_DECK_TITLE, starred, srs, learning
            )
        ]
        series_decks = [
            _summarize(f"series:{sid}", DeckKind.SERIES, sid, titles[sid], ids, srs, learning)
            for sid, ids in by_series.items()
        ]
        series_decks.sort(key=lambda d: (-d.word_count, d.title))
        return DeckList(items + series_decks, now)


def _summarize(
    key: str,
    kind: DeckKind,
    series_id: int | None,
    title: str,
    ids: set[int],
    srs: dict[int, EntrySrsSummary],
    learning: set[int],
) -> DeckSummary:
    return DeckSummary(
        key=key,
        kind=kind.value,
        series_id=series_id,
        title=title,
        word_count=len(ids),
        reviewed_count=sum(1 for i in ids if i in srs and srs[i].review_count > 0),
        due_count=sum(srs[i].due_count for i in ids if i in srs and i in learning),
    )
