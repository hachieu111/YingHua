from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends

from app.container import Container, get_container
from app.modules.library.application.public import GetChapterUseCase, ListSeriesCandidatesUseCase
from app.modules.library.infrastructure.public import SqlLibraryUnitOfWork
from app.modules.suggestions.application.ports import SuggestionUnitOfWork
from app.modules.suggestions.application.use_cases.accept_suggestion import AcceptSuggestionUseCase
from app.modules.suggestions.application.use_cases.dismissals import (
    DismissSuggestionUseCase,
    ListDismissedUseCase,
    RestoreSuggestionUseCase,
)
from app.modules.suggestions.application.use_cases.get_chapter_coverage import GetChapterCoverageUseCase
from app.modules.suggestions.application.use_cases.list_suggestions import ListSuggestionsUseCase
from app.modules.suggestions.application.use_cases.recommend_series import RecommendSeriesUseCase
from app.modules.suggestions.infrastructure.adapters import (
    DictionaryTermHints,
    LibraryChapterSource,
    LibrarySeriesCandidateSource,
    SettingsLearnerLevelSource,
)
from app.modules.suggestions.infrastructure.uow import SqlSuggestionUnitOfWork
from app.modules.vocab.api.public import build_vocab_services


@dataclass(slots=True)
class SuggestionServices:
    list_suggestions: ListSuggestionsUseCase
    accept: AcceptSuggestionUseCase
    dismiss: DismissSuggestionUseCase
    restore: RestoreSuggestionUseCase
    list_dismissed: ListDismissedUseCase
    recommend_series: RecommendSeriesUseCase
    coverage: GetChapterCoverageUseCase


def build_suggestion_services(container: Container) -> SuggestionServices:
    def uow_factory() -> SuggestionUnitOfWork:
        return SqlSuggestionUnitOfWork(container.session_factory)

    factory = container.session_factory
    chapters = LibraryChapterSource(GetChapterUseCase(lambda: SqlLibraryUnitOfWork(factory), container.clock))
    hints = DictionaryTermHints(factory)
    levels = SettingsLearnerLevelSource(factory)
    library = SqlLibraryUnitOfWork
    return SuggestionServices(
        list_suggestions=ListSuggestionsUseCase(
            uow_factory, chapters, hints, SettingsLearnerLevelSource(factory)
        ),
        accept=AcceptSuggestionUseCase(
            uow_factory, chapters, build_vocab_services(container).save_word, hints
        ),
        dismiss=DismissSuggestionUseCase(uow_factory, container.clock),
        restore=RestoreSuggestionUseCase(uow_factory),
        list_dismissed=ListDismissedUseCase(uow_factory, hints),
        recommend_series=RecommendSeriesUseCase(
            LibrarySeriesCandidateSource(ListSeriesCandidatesUseCase(lambda: library(factory))), levels
        ),
        coverage=GetChapterCoverageUseCase(uow_factory, chapters, hints, levels),
    )


def get_suggestion_services(container: Container = Depends(get_container)) -> SuggestionServices:
    return build_suggestion_services(container)
