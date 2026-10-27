from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Query

from app.container import Container, get_container
from app.modules.library.application.public import LibraryPageAccess
from app.modules.library.infrastructure.public import SqlLibraryUnitOfWork
from app.modules.review.application.public import CreateCardsForEntryUseCase
from app.modules.review.infrastructure.public import FsrsScheduler
from app.modules.vocab.application.dto import ListVocabQuery
from app.modules.vocab.application.ports import VocabUnitOfWork
from app.modules.vocab.application.use_cases.delete_context import DeleteContextUseCase
from app.modules.vocab.application.use_cases.delete_saved_sentence import DeleteSavedSentenceUseCase
from app.modules.vocab.application.use_cases.delete_vocab import DeleteVocabUseCase
from app.modules.vocab.application.use_cases.export_vocab import ExportVocabUseCase
from app.modules.vocab.application.use_cases.get_saved_status import GetSavedStatusUseCase
from app.modules.vocab.application.use_cases.get_vocab import GetVocabUseCase
from app.modules.vocab.application.use_cases.list_decks import ListDecksUseCase
from app.modules.vocab.application.use_cases.list_saved_sentences import ListSavedSentencesUseCase
from app.modules.vocab.application.use_cases.list_vocab import ListVocabUseCase
from app.modules.vocab.application.use_cases.save_all_page_words import SaveAllPageWordsUseCase
from app.modules.vocab.application.use_cases.save_sentence import SaveSentenceUseCase
from app.modules.vocab.application.use_cases.save_word import SaveWordUseCase
from app.modules.vocab.application.use_cases.update_saved_sentence import UpdateSavedSentenceUseCase
from app.modules.vocab.application.use_cases.update_vocab import UpdateVocabUseCase
from app.modules.vocab.infrastructure.public import DictionaryTermAdapter, SqlVocabUnitOfWork
from app.modules.vocab.infrastructure.snippet_cropper import PillowSnippetCropper


@dataclass(slots=True)
class VocabServices:
    save_word: SaveWordUseCase
    list_vocab: ListVocabUseCase
    export_vocab: ExportVocabUseCase
    get_vocab: GetVocabUseCase
    update_vocab: UpdateVocabUseCase
    delete_context: DeleteContextUseCase
    delete_vocab: DeleteVocabUseCase
    list_decks: ListDecksUseCase
    save_sentence: SaveSentenceUseCase
    list_sentences: ListSavedSentencesUseCase
    update_sentence: UpdateSavedSentenceUseCase
    delete_sentence: DeleteSavedSentenceUseCase
    save_all_words: SaveAllPageWordsUseCase
    saved_status: GetSavedStatusUseCase


def build_vocab_services(container: Container) -> VocabServices:
    def uow_factory() -> VocabUnitOfWork:
        return SqlVocabUnitOfWork(container.session_factory)

    clock, settings, storage = container.clock, container.settings, container.storage
    pages = LibraryPageAccess(lambda: SqlLibraryUnitOfWork(container.session_factory), clock)
    dictionary = DictionaryTermAdapter(container.session_factory)
    save_word = SaveWordUseCase(
        uow_factory,
        pages,
        dictionary,
        PillowSnippetCropper(settings.max_upload_mb * 1024 * 1024),
        CreateCardsForEntryUseCase(FsrsScheduler()),
        storage,
        clock,
    )
    return VocabServices(
        save_word=save_word,
        list_vocab=ListVocabUseCase(uow_factory, pages, dictionary, clock),
        export_vocab=ExportVocabUseCase(uow_factory, pages, clock),
        get_vocab=GetVocabUseCase(uow_factory, pages, dictionary, clock),
        update_vocab=UpdateVocabUseCase(uow_factory, pages, dictionary, clock, settings.note_max_chars),
        delete_context=DeleteContextUseCase(uow_factory, storage, clock),
        delete_vocab=DeleteVocabUseCase(uow_factory, storage, clock),
        list_decks=ListDecksUseCase(uow_factory, pages, clock),
        save_sentence=SaveSentenceUseCase(uow_factory, pages, clock, settings.note_max_chars),
        list_sentences=ListSavedSentencesUseCase(uow_factory, pages),
        update_sentence=UpdateSavedSentenceUseCase(uow_factory, pages, clock, settings.note_max_chars),
        delete_sentence=DeleteSavedSentenceUseCase(uow_factory, clock),
        save_all_words=SaveAllPageWordsUseCase(uow_factory, pages, save_word),
        saved_status=GetSavedStatusUseCase(uow_factory),
    )


def get_vocab_services(container: Container = Depends(get_container)) -> VocabServices:
    return build_vocab_services(container)


def get_list_vocab_query(
    status_filter: str | None = Query(default=None, alias="status", description="learning | known | ignored"),
    hsk: str | None = Query(default=None, description="1..9 hoặc `none` (Ngoài HSK)"),
    q: str | None = Query(default=None, max_length=64, description="Tìm theo từ, pinyin, nghĩa"),
    starred: bool | None = Query(default=None, description="true: chỉ từ đánh dấu sao"),
    series_id: int | None = Query(default=None, ge=1, description="Chỉ từ gặp trong truyện này"),
    due: bool | None = Query(
        default=None,
        description="true: chỉ từ có thẻ đến hạn (như /cards/due); false: từ không có thẻ đến hạn",
    ),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> ListVocabQuery:
    """Bộ lọc danh sách sổ tay, dùng chung cho API người dùng và API quản trị (F07.07, F13.07)."""
    return ListVocabQuery(status_filter, hsk, q, starred, series_id, due, page, size)


def get_export_query(
    status_filter: str | None = Query(default=None, alias="status", description="learning | known | ignored"),
    hsk: str | None = Query(default=None, description="1..9 hoặc `none` (Ngoài HSK)"),
    q: str | None = Query(default=None, max_length=64, description="Tìm theo từ, pinyin, nghĩa"),
    starred: bool | None = Query(default=None, description="true: chỉ từ đánh dấu sao"),
    series_id: int | None = Query(default=None, ge=1, description="Chỉ từ gặp trong truyện này"),
    due: bool | None = Query(default=None, description="true: chỉ từ có thẻ đến hạn"),
) -> ListVocabQuery:
    """Bộ lọc khi xuất sổ tay (F07.08): cùng bộ lọc với danh sách nhưng không phân trang."""
    return ListVocabQuery(status_filter, hsk, q, starred, series_id, due)
