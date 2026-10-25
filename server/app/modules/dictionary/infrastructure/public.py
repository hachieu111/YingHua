"""Hiện thực M06 mà tầng lắp ghép của module khác được dùng."""

from __future__ import annotations

from app.modules.dictionary.infrastructure.level_checker import JiebaExampleLevelChecker
from app.modules.dictionary.infrastructure.repositories import SqlLookupEventRepository
from app.modules.dictionary.infrastructure.text_tools import JiebaTokenizer, PypinyinProvider
from app.modules.dictionary.infrastructure.uow import SqlDictionaryUnitOfWork

__all__ = [
    "JiebaExampleLevelChecker",
    "JiebaTokenizer",
    "PypinyinProvider",
    "SqlDictionaryUnitOfWork",
    "SqlLookupEventRepository",
]
