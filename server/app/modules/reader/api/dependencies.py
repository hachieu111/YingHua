from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from fastapi import Depends, Header

from app.container import Container, get_container
from app.core.external_call_log import SqlLlmCallLogWriter
from app.modules.dictionary.infrastructure.public import JiebaExampleLevelChecker
from app.modules.library.application.public import LibraryPageAccess
from app.modules.library.infrastructure.public import SqlLibraryUnitOfWork
from app.modules.reader.application.ports import GrammarAnalyzer, ReaderUnitOfWork
from app.modules.reader.application.use_cases.analyze_grammar import AnalyzeGrammarUseCase, GrammarConfig
from app.modules.reader.application.use_cases.clear_annotations import ClearAnnotationsUseCase
from app.modules.reader.application.use_cases.delete_bubble_edit import DeleteBubbleEditUseCase
from app.modules.reader.application.use_cases.get_annotations import GetAnnotationsUseCase
from app.modules.reader.application.use_cases.get_reading import GetReadingUseCase
from app.modules.reader.application.use_cases.list_bookmarks import ListBookmarksUseCase
from app.modules.reader.application.use_cases.list_bubble_edits import ListBubbleEditsUseCase
from app.modules.reader.application.use_cases.lookup_bubble_word import LookupBubbleWordUseCase
from app.modules.reader.application.use_cases.save_annotations import SaveAnnotationsUseCase
from app.modules.reader.application.use_cases.save_bubble_edit import SaveBubbleEditUseCase
from app.modules.reader.application.use_cases.set_bookmark import SetBookmarkUseCase
from app.modules.reader.infrastructure.adapters import SettingsTimezoneSource
from app.modules.reader.infrastructure.dictionary_lookup import DictionaryLookupAdapter
from app.modules.reader.infrastructure.gemini_grammar import DisabledGrammarAnalyzer, GeminiGrammarAnalyzer
from app.modules.reader.infrastructure.uow import SqlReaderUnitOfWork

GUEST_SESSION_HEADER = "X-Guest-Session"


@dataclass(slots=True)
class ReaderServices:
    get_reading: GetReadingUseCase
    lookup: LookupBubbleWordUseCase
    save_edit: SaveBubbleEditUseCase
    delete_edit: DeleteBubbleEditUseCase
    set_bookmark: SetBookmarkUseCase
    list_bookmarks: ListBookmarksUseCase
    save_annotations: SaveAnnotationsUseCase
    clear_annotations: ClearAnnotationsUseCase
    get_annotations: GetAnnotationsUseCase
    list_edits: ListBubbleEditsUseCase
    analyze_grammar: AnalyzeGrammarUseCase


def build_reader_services(container: Container) -> ReaderServices:
    def uow_factory() -> ReaderUnitOfWork:
        return SqlReaderUnitOfWork(container.session_factory)

    clock, settings = container.clock, container.settings
    pages = LibraryPageAccess(lambda: SqlLibraryUnitOfWork(container.session_factory), clock)
    return ReaderServices(
        get_reading=GetReadingUseCase(uow_factory, pages),
        lookup=LookupBubbleWordUseCase(
            uow_factory,
            pages,
            DictionaryLookupAdapter(container.session_factory, container.clock),
            clock,
            settings.guest_lookup_limit,
            timedelta(hours=settings.guest_session_hours),
        ),
        save_edit=SaveBubbleEditUseCase(uow_factory, pages, clock),
        delete_edit=DeleteBubbleEditUseCase(uow_factory, pages, clock),
        set_bookmark=SetBookmarkUseCase(uow_factory, pages, clock),
        list_bookmarks=ListBookmarksUseCase(uow_factory, pages),
        save_annotations=SaveAnnotationsUseCase(uow_factory, pages, clock),
        clear_annotations=ClearAnnotationsUseCase(uow_factory, pages, clock),
        get_annotations=GetAnnotationsUseCase(uow_factory, pages),
        list_edits=ListBubbleEditsUseCase(uow_factory, pages),
        analyze_grammar=AnalyzeGrammarUseCase(
            uow_factory,
            pages,
            build_grammar_analyzer(container),
            JiebaExampleLevelChecker(container.session_factory),
            SettingsTimezoneSource(container.session_factory),
            container.ai_policies.grammar,
            container.single_flight,
            clock,
            GrammarConfig(settings.llm_timeout_seconds, settings.llm_model),
        ),
    )


def build_grammar_analyzer(container: Container) -> GrammarAnalyzer:
    """Gemini khi có khóa API và nhà cung cấp là gemini; không thì adapter "tắt". Công tắc `llm_enabled` do
    quản trị đặt (F13.05) được use case kiểm trước khi gọi. Khóa chỉ đọc từ cấu hình, không bao giờ log."""
    settings = container.settings
    key = settings.llm_api_key
    if key is not None and key.get_secret_value() and settings.llm_provider == "gemini":
        return GeminiGrammarAnalyzer(
            key,
            settings.llm_model,
            settings.llm_timeout_seconds,
            SqlLlmCallLogWriter(container.session_factory).record,
            thinking_level=settings.llm_thinking_level,
        )
    return DisabledGrammarAnalyzer()


def get_reader_services(container: Container = Depends(get_container)) -> ReaderServices:
    return build_reader_services(container)


def get_guest_session_id(
    x_guest_session: str | None = Header(default=None, alias=GUEST_SESSION_HEADER),
) -> uuid.UUID | None:
    """Mã phiên ẩn danh của Khách (F05.04). Giá trị sai định dạng coi như chưa có phiên."""
    if not x_guest_session:
        return None
    try:
        return uuid.UUID(x_guest_session)
    except ValueError:
        return None
