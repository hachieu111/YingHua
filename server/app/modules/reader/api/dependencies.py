from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from fastapi import Depends, Header

from app.container import Container, get_container
from app.modules.library.application.public import LibraryPageAccess
from app.modules.library.infrastructure.public import SqlLibraryUnitOfWork
from app.modules.reader.application.ports import ReaderUnitOfWork
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
from app.modules.reader.infrastructure.dictionary_lookup import DictionaryLookupAdapter
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
            DictionaryLookupAdapter(container.session_factory),
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
    )


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
