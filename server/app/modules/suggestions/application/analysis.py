"""Gom từ của một chương (dùng chung cho danh sách gợi ý F10.01 và nhận gợi ý F10.02)."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.auth.application.public import Identity
from app.modules.suggestions.application.ports import ChapterSource, SuggestionUnitOfWork, TermHints
from app.modules.suggestions.domain.entities import BubbleTokens, TermStats
from app.modules.suggestions.domain.rules import collect_stats, fold_reduplication, reduplication_root

STATUS_DONE = "done"
STATUS_PENDING = (
    "queued",
    "running",
)  # trang `failed` không còn đang xử lý nên không giữ chương ở "processing"

READY = "ready"
PROCESSING = "processing"


@dataclass(frozen=True, slots=True)
class ChapterAnalysis:
    status: str  # ready | processing
    stats: dict[str, TermStats]


async def analyze_chapter(
    chapters: ChapterSource, uow: SuggestionUnitOfWork, identity: Identity, chapter_id: int
) -> ChapterAnalysis:
    """Từ và tần suất của các trang đã "Xong"; `processing` khi còn trang chưa có bản dịch xong."""
    pages = sorted(await chapters.pages_of(identity, chapter_id), key=lambda p: p.page_no)
    pending = any(p.translation_status is None or p.translation_status in STATUS_PENDING for p in pages)
    bubbles: list[BubbleTokens] = []
    cache: dict[int, list[BubbleTokens]] = {}
    for page in pages:
        if page.translation_status != STATUS_DONE or page.translation_id is None:
            continue
        if page.translation_id not in cache:
            rows = await uow.bubbles.list_by_translation(page.translation_id)
            cache[page.translation_id] = [
                BubbleTokens(page.page_id, page.page_no, b.id, b.idx, b.tokens)
                for b in sorted(rows, key=lambda b: b.idx)
            ]
        # Trang dùng chung một bản dịch (ảnh trùng) vẫn đếm riêng và có vị trí trang riêng.
        bubbles.extend(
            BubbleTokens(page.page_id, page.page_no, b.bubble_id, b.idx, b.tokens)
            for b in cache[page.translation_id]
        )
    return ChapterAnalysis(PROCESSING if pending else READY, collect_stats(bubbles))


async def fold_reduplicated(stats: dict[str, TermStats], hints: TermHints) -> dict[str, TermStats]:
    """Gộp dạng lặp (看看 -> 看, 学习学习 -> 学习) về từ gốc khi từ gốc có trong từ điển (F10.01)."""
    roots = sorted({root for term in stats if (root := reduplication_root(term)) is not None})
    if not roots:
        return dict(stats)
    return fold_reduplication(stats, await hints.known_terms(roots))
