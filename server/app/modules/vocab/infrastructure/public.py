"""Hiện thực M07 mà tầng lắp ghép của module khác được dùng (chỉ ở tầng hạ tầng)."""

from __future__ import annotations

from app.modules.vocab.infrastructure.card_source import SqlVocabCardSource
from app.modules.vocab.infrastructure.quiz_source import SqlVocabQuizSource
from app.modules.vocab.infrastructure.suggestion_source import SqlVocabSuggestionSource
from app.modules.vocab.infrastructure.term_dictionary import DictionaryTermAdapter
from app.modules.vocab.infrastructure.uow import SqlVocabUnitOfWork

__all__ = [
    "DictionaryTermAdapter",
    "SqlVocabCardSource",
    "SqlVocabQuizSource",
    "SqlVocabSuggestionSource",
    "SqlVocabUnitOfWork",
]
