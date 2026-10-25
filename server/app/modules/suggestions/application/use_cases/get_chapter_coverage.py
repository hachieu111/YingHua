from __future__ import annotations

from collections.abc import Callable

from app.modules.auth.application.public import Identity
from app.modules.suggestions.application.analysis import analyze_chapter
from app.modules.suggestions.application.dto import ChapterCoverage
from app.modules.suggestions.application.ports import (
    ChapterSource,
    LearnerLevelSource,
    SuggestionUnitOfWork,
    TermHints,
)
from app.modules.suggestions.domain.rules import coverage_percent, coverage_status


class GetChapterCoverageUseCase:
    """F10.05 — Độ phủ từ vựng của chương: "đã nắm X/Y từ HSK n" (US-NH-73).

    Y = số từ khác nhau trong chương có cấp HSK từ 1 đến n (bảng HSK, hoặc cấp cao nhất của chữ cấu thành,
    F06.08); X = số từ trong đó đã có trong sổ tay ở MỌI trạng thái. Chưa khai báo trình độ thì tính trên mọi
    từ có cấp HSK và trả `hsk_level=None` để giao diện nhắc khai báo. Tính khi gọi, không lưu; còn trang
    chưa xong → `processing` (tạm tính); không có từ để tính → `empty` (không hiển thị 0/0). Kiểm quyền đọc
    chương như F10.01 (không đọc được → 404).
    """

    def __init__(
        self,
        uow_factory: Callable[[], SuggestionUnitOfWork],
        chapters: ChapterSource,
        hints: TermHints,
        levels: LearnerLevelSource,
    ) -> None:
        self._uow_factory = uow_factory
        self._chapters = chapters
        self._hints = hints
        self._levels = levels

    async def execute(self, identity: Identity, chapter_id: int) -> ChapterCoverage:
        level = await self._levels.hsk_level_of(identity.user_id)
        async with self._uow_factory() as uow:
            analysis = await analyze_chapter(self._chapters, uow, identity, chapter_id)
            term_levels = await self._hints.hsk_levels(list(analysis.stats))
            in_scope = [
                t for t, lv in term_levels.items() if lv is not None and (level is None or lv <= level)
            ]
            known = await uow.saved.saved_terms(identity.user_id, in_scope)
        total = len(in_scope)
        return ChapterCoverage(
            hsk_level=level,
            known_terms=len(known),
            total_terms=total,
            percent=coverage_percent(len(known), total),
            status=coverage_status(analysis.status == "processing", total),
        )
