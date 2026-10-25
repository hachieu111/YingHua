from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends

from app.container import Container, get_container
from app.modules.imaging.application.ports import ImagingUnitOfWork
from app.modules.imaging.application.use_cases.download_page_image import DownloadPageImageUseCase
from app.modules.imaging.application.use_cases.get_page_status import GetPageStatusUseCase
from app.modules.imaging.application.use_cases.list_translations import ListTranslationsUseCase
from app.modules.imaging.application.use_cases.retranslate_page import RetranslatePageUseCase
from app.modules.imaging.application.use_cases.retry_translation import RetryTranslationUseCase
from app.modules.imaging.infrastructure.uow import SqlImagingUnitOfWork
from app.modules.library.application.public import LibraryPageAccess
from app.modules.library.infrastructure.public import SqlLibraryUnitOfWork


@dataclass(slots=True)
class ImagingServices:
    retranslate: RetranslatePageUseCase
    page_status: GetPageStatusUseCase
    download: DownloadPageImageUseCase
    list_translations: ListTranslationsUseCase
    retry: RetryTranslationUseCase


def build_imaging_services(container: Container) -> ImagingServices:
    def uow_factory() -> ImagingUnitOfWork:
        return SqlImagingUnitOfWork(container.session_factory)

    clock, storage = container.clock, container.storage
    pages = LibraryPageAccess(lambda: SqlLibraryUnitOfWork(container.session_factory), clock)
    return ImagingServices(
        retranslate=RetranslatePageUseCase(uow_factory, pages, clock),
        page_status=GetPageStatusUseCase(uow_factory, pages),
        download=DownloadPageImageUseCase(uow_factory, pages, storage),
        list_translations=ListTranslationsUseCase(uow_factory),
        retry=RetryTranslationUseCase(uow_factory, clock),
    )


def get_imaging_services(container: Container = Depends(get_container)) -> ImagingServices:
    return build_imaging_services(container)
