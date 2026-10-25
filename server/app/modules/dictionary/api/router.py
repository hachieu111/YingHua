from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.container import Container, get_container
from app.core.errors import PayloadTooLargeError
from app.modules.auth.api.public import Identity, get_optional_identity, require_admin
from app.modules.dictionary.api.schemas import (
    CharacterResponse,
    CharactersResponse,
    ImportReportResponse,
    LookupResponse,
    SearchPageResponse,
    SegmentRequest,
    SegmentResponse,
    TokenResponse,
    WordOfTheDayResponse,
)
from app.modules.dictionary.application.ports import DictionaryUnitOfWork
from app.modules.dictionary.application.use_cases.decompose_characters import DecomposeCharactersUseCase
from app.modules.dictionary.application.use_cases.import_dictionary import ImportDictionaryUseCase
from app.modules.dictionary.application.use_cases.import_hsk_list import ImportHskListUseCase
from app.modules.dictionary.application.use_cases.lookup_word import LookupWordUseCase
from app.modules.dictionary.application.use_cases.search_words import SearchWordsUseCase
from app.modules.dictionary.application.use_cases.segment_sentence import SegmentSentenceUseCase
from app.modules.dictionary.application.use_cases.word_of_the_day import WordOfTheDayUseCase
from app.modules.dictionary.infrastructure.parsers import parse_cvdict, parse_hsk
from app.modules.dictionary.infrastructure.text_tools import JiebaTokenizer, PypinyinProvider
from app.modules.dictionary.infrastructure.uow import SqlDictionaryUnitOfWork
from app.modules.settings.application.public import GetSettingsUseCase, UserSettings
from app.modules.settings.infrastructure.public import SqlSettingsUnitOfWork

router = APIRouter(prefix="/dictionary", tags=["M06 Từ điển"])
admin_router = APIRouter(prefix="/admin/dictionary", tags=["M06 Từ điển (quản trị)"])

MAX_IMPORT_MB = 50
_tokenizer = JiebaTokenizer()
_pinyin = PypinyinProvider()


def _uow_factory(container: Container) -> Callable[[], DictionaryUnitOfWork]:
    def make() -> DictionaryUnitOfWork:
        return SqlDictionaryUnitOfWork(container.session_factory)

    return make


async def _user_settings(container: Container, identity: Identity | None) -> UserSettings | None:
    if identity is None:
        return None
    return await GetSettingsUseCase(lambda: SqlSettingsUnitOfWork(container.session_factory)).execute(
        identity
    )


@router.get(
    "/lookup", response_model=LookupResponse, summary="Tra cứu chi tiết một từ (F06.01, F06.03, F06.05)"
)
async def lookup(
    term: str = Query(min_length=1, max_length=64, description="Từ tiếng Trung cần tra"),
    identity: Identity | None = Depends(get_optional_identity),
    container: Container = Depends(get_container),
) -> LookupResponse:
    # TODO(F05.04): giới hạn 5 lượt tra mỗi phiên cho Khách khi có trình đọc thử (Giai đoạn 3).
    settings = await _user_settings(container, identity)
    use_case = LookupWordUseCase(_uow_factory(container), _pinyin)
    result = await use_case.execute(
        term, identity, include_specialized=settings.show_xianxia if settings else True
    )
    return LookupResponse.from_result(result)


@router.get(
    "/search", response_model=SearchPageResponse, summary="Tìm từ theo chữ Hán, pinyin, nghĩa Việt (F06.02)"
)
async def search(
    q: str = Query(min_length=1, max_length=64),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=50),
    container: Container = Depends(get_container),
) -> SearchPageResponse:
    return SearchPageResponse.from_page(
        await SearchWordsUseCase(_uow_factory(container)).execute(q, page, size)
    )


@router.post("/segment", response_model=SegmentResponse, summary="Tách câu thành từ kèm pinyin (F06.04)")
async def segment(body: SegmentRequest) -> SegmentResponse:
    tokens = await SegmentSentenceUseCase(_tokenizer, _pinyin).execute(body.text)
    return SegmentResponse(tokens=[TokenResponse.from_entity(t) for t in tokens])


@router.get("/characters", response_model=CharactersResponse, summary="Phân rã chữ Hán (F06.05)")
async def characters(
    text: str = Query(min_length=1, max_length=20, description="Một chữ hoặc một từ nhiều chữ"),
    identity: Identity | None = Depends(get_optional_identity),
    container: Container = Depends(get_container),
) -> CharactersResponse:
    breakdown = await DecomposeCharactersUseCase(_uow_factory(container)).execute(text, identity)
    return CharactersResponse(characters=[CharacterResponse.from_entity(c) for c in breakdown])


@router.get(
    "/word-of-the-day", response_model=WordOfTheDayResponse, summary="Từ vựng trong ngày theo trình độ HSK"
)
async def word_of_the_day(
    identity: Identity | None = Depends(get_optional_identity),
    container: Container = Depends(get_container),
) -> WordOfTheDayResponse:
    settings = await _user_settings(container, identity)
    use_case = WordOfTheDayUseCase(_uow_factory(container), container.clock)
    return WordOfTheDayResponse.from_entity(await use_case.execute(settings.hsk_level if settings else None))


async def _read_upload(file: UploadFile) -> bytes:
    data = await file.read(MAX_IMPORT_MB * 1024 * 1024 + 1)
    if len(data) > MAX_IMPORT_MB * 1024 * 1024:
        raise PayloadTooLargeError(f"Tệp tối đa {MAX_IMPORT_MB} MB")
    return data


@admin_router.post(
    "/entries/import", response_model=ImportReportResponse, summary="Nạp / cập nhật từ điển (F06.06)"
)
async def import_entries(
    file: UploadFile = File(description="Tệp từ điển định dạng CVDICT (JSON)"),
    admin: Identity = Depends(require_admin),
    container: Container = Depends(get_container),
) -> ImportReportResponse:
    rows = parse_cvdict(await _read_upload(file))
    report = await ImportDictionaryUseCase(_uow_factory(container)).execute(admin, rows)
    return ImportReportResponse.from_report(report)


@admin_router.post(
    "/hsk/import", response_model=ImportReportResponse, summary="Nạp / cập nhật danh sách HSK (F06.07)"
)
async def import_hsk(
    file: UploadFile = File(description="complete-hsk-vocabulary (JSON) hoặc CSV `từ,cấp[,pinyin]`"),
    admin: Identity = Depends(require_admin),
    container: Container = Depends(get_container),
) -> ImportReportResponse:
    rows, rejected = parse_hsk(await _read_upload(file))
    report = await ImportHskListUseCase(_uow_factory(container)).execute(admin, rows, rejected)
    return ImportReportResponse.from_report(report)
