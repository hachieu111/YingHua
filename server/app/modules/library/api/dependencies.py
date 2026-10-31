from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from fastapi import Depends

from app.container import Container, get_container
from app.modules.library.application.ports import LibraryUnitOfWork
from app.modules.library.application.use_cases.add_to_library import AddToLibraryUseCase
from app.modules.library.application.use_cases.create_chapter import CreateChapterUseCase
from app.modules.library.application.use_cases.create_series import CreateSeriesUseCase
from app.modules.library.application.use_cases.delete_chapter import DeleteChapterUseCase
from app.modules.library.application.use_cases.delete_page import DeletePageUseCase
from app.modules.library.application.use_cases.delete_series import DeleteSeriesUseCase
from app.modules.library.application.use_cases.get_chapter import GetChapterUseCase
from app.modules.library.application.use_cases.get_file import GetFileUseCase
from app.modules.library.application.use_cases.get_page import GetPageUseCase
from app.modules.library.application.use_cases.get_series import GetSeriesUseCase
from app.modules.library.application.use_cases.list_continue_reading import ListContinueReadingUseCase
from app.modules.library.application.use_cases.list_library import ListLibraryUseCase
from app.modules.library.application.use_cases.list_quick_uploads import ListQuickUploadsUseCase
from app.modules.library.application.use_cases.list_series import ListSeriesUseCase
from app.modules.library.application.use_cases.quick_upload import QuickUploadUseCase
from app.modules.library.application.use_cases.rate_series import RateSeriesUseCase
from app.modules.library.application.use_cases.remove_from_library import RemoveFromLibraryUseCase
from app.modules.library.application.use_cases.save_progress import SaveProgressUseCase
from app.modules.library.application.use_cases.set_favorite import SetFavoriteUseCase
from app.modules.library.application.use_cases.set_series_cover import SetSeriesCoverUseCase
from app.modules.library.application.use_cases.update_chapter import UpdateChapterUseCase
from app.modules.library.application.use_cases.update_series import UpdateSeriesUseCase
from app.modules.library.application.use_cases.upload_pages import UploadPagesUseCase
from app.modules.library.infrastructure.uow import SqlLibraryUnitOfWork


@dataclass(slots=True)
class LibraryServices:
    max_upload_bytes: int
    list_series: ListSeriesUseCase
    get_series: GetSeriesUseCase
    create_series: CreateSeriesUseCase
    update_series: UpdateSeriesUseCase
    delete_series: DeleteSeriesUseCase
    set_cover: SetSeriesCoverUseCase
    create_chapter: CreateChapterUseCase
    update_chapter: UpdateChapterUseCase
    delete_chapter: DeleteChapterUseCase
    get_chapter: GetChapterUseCase
    upload_pages: UploadPagesUseCase
    quick_upload: QuickUploadUseCase
    list_quick_uploads: ListQuickUploadsUseCase
    get_page: GetPageUseCase
    delete_page: DeletePageUseCase
    save_progress: SaveProgressUseCase
    list_continue: ListContinueReadingUseCase
    list_library: ListLibraryUseCase
    add_to_library: AddToLibraryUseCase
    remove_from_library: RemoveFromLibraryUseCase
    set_favorite: SetFavoriteUseCase
    rate_series: RateSeriesUseCase
    get_file: GetFileUseCase


def build_library_services(container: Container) -> LibraryServices:
    def uow_factory() -> LibraryUnitOfWork:
        return SqlLibraryUnitOfWork(container.session_factory)

    clock, storage, settings = container.clock, container.storage, container.settings
    return LibraryServices(
        max_upload_bytes=settings.max_upload_mb * 1024 * 1024,
        list_series=ListSeriesUseCase(uow_factory, clock),
        get_series=GetSeriesUseCase(uow_factory, clock),
        create_series=CreateSeriesUseCase(uow_factory, clock),
        update_series=UpdateSeriesUseCase(uow_factory, clock),
        delete_series=DeleteSeriesUseCase(uow_factory, clock, storage),
        set_cover=SetSeriesCoverUseCase(uow_factory, clock, storage),
        create_chapter=CreateChapterUseCase(uow_factory, clock),
        update_chapter=UpdateChapterUseCase(uow_factory, clock),
        delete_chapter=DeleteChapterUseCase(uow_factory, clock, storage),
        get_chapter=GetChapterUseCase(uow_factory, clock),
        upload_pages=UploadPagesUseCase(uow_factory, clock, storage),
        quick_upload=QuickUploadUseCase(
            uow_factory, clock, storage, timedelta(days=settings.upload_retention_days)
        ),
        list_quick_uploads=ListQuickUploadsUseCase(uow_factory),
        get_page=GetPageUseCase(uow_factory, clock),
        delete_page=DeletePageUseCase(uow_factory, clock, storage),
        save_progress=SaveProgressUseCase(uow_factory, clock),
        list_continue=ListContinueReadingUseCase(uow_factory),
        list_library=ListLibraryUseCase(uow_factory, clock),
        add_to_library=AddToLibraryUseCase(uow_factory, clock),
        remove_from_library=RemoveFromLibraryUseCase(uow_factory),
        set_favorite=SetFavoriteUseCase(uow_factory, clock),
        rate_series=RateSeriesUseCase(uow_factory, clock),
        get_file=GetFileUseCase(uow_factory, clock, storage),
    )


def get_library_services(container: Container = Depends(get_container)) -> LibraryServices:
    return build_library_services(container)
