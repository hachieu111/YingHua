"""Adapter của M10 với module khác qua giao diện công khai: chương (M03), từ điển (M06), cài đặt (M02)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.glosses import best_gloss
from app.modules.auth.application.public import Identity, Role
from app.modules.dictionary.application.public import resolve_hsk
from app.modules.dictionary.infrastructure.public import SqlDictionaryUnitOfWork
from app.modules.library.application.public import GetChapterUseCase, ListSeriesCandidatesUseCase
from app.modules.settings.application.public import GetSettingsUseCase
from app.modules.settings.infrastructure.public import SqlSettingsUnitOfWork
from app.modules.suggestions.application.ports import ChapterPage, TermBrief
from app.modules.suggestions.domain.entities import SeriesCandidate


class LibraryChapterSource:
    """Trang của chương và trạng thái bản dịch, có kiểm quyền đọc chương (F03.10)."""

    def __init__(self, get_chapter: GetChapterUseCase) -> None:
        self._get_chapter = get_chapter

    async def pages_of(self, identity: Identity, chapter_id: int) -> list[ChapterPage]:
        detail = await self._get_chapter.execute(identity, chapter_id)
        return [
            ChapterPage(
                v.page.id,
                v.page.page_no,
                v.page.translation_id,
                v.translation.status.value if v.translation else None,
            )
            for v in detail.pages
        ]


class DictionaryTermHints:
    """Cấp HSK và nghĩa của nhiều từ cùng lúc từ M06; mọi lời gọi chỉ đọc, dùng phiên riêng."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def hsk_levels(self, terms: Sequence[str]) -> dict[str, int | None]:
        if not terms:
            return {}
        chars = {c for term in terms for c in term}
        async with SqlDictionaryUnitOfWork(self._session_factory) as uow:
            table = await uow.reader.get_hsk_levels([*terms, *chars])
        return {term: resolve_hsk(term, table).level for term in terms}

    async def known_terms(self, terms: Sequence[str]) -> set[str]:
        if not terms:
            return set()
        async with SqlDictionaryUnitOfWork(self._session_factory) as uow:
            return set(await uow.reader.find_entry_ids(terms))

    async def briefs(self, terms: Sequence[str]) -> dict[str, TermBrief]:
        if not terms:
            return {}
        async with SqlDictionaryUnitOfWork(self._session_factory) as uow:
            entries = await uow.reader.brief_entries(terms)
        return {
            term: TermBrief(e.pinyin, best_gloss(d.gloss for d in e.definitions) or None)
            for term, e in entries.items()
        }


class SettingsLearnerLevelSource:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def hsk_level_of(self, user_id: int) -> int | None:
        identity = Identity(user_id=user_id, role=Role.USER, session_id="")
        use_case = GetSettingsUseCase(lambda: SqlSettingsUnitOfWork(self._session_factory))
        return (await use_case.execute(identity)).hsk_level


class LibrarySeriesCandidateSource:
    """Truyện công khai ứng viên từ M03 (đã loại truyện riêng tư của người khác)."""

    def __init__(self, list_candidates: ListSeriesCandidatesUseCase) -> None:
        self._list_candidates = list_candidates

    async def candidates(self, identity: Identity, hsk_min: int, hsk_max: int) -> list[SeriesCandidate]:
        rows = await self._list_candidates.execute(identity, hsk_min, hsk_max)
        return [
            SeriesCandidate(
                series_id=r.view.series.id,
                title_vi=r.view.series.title_vi,
                title_zh=r.view.series.title_zh,
                cover_file_id=r.view.series.cover_file_id,
                est_hsk_level=r.view.series.est_hsk_level,
                genres=tuple(r.view.series.genres),
                rating_avg=r.view.rating_avg,
                rating_count=r.view.rating_count,
                chapter_count=r.view.chapter_count,
                library_count=r.library_count,
                in_library=r.view.in_library,
                finished=r.finished,
            )
            for r in rows
        ]
