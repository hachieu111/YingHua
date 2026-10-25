"""Bề mặt công khai của M06 cho module khác (M07 cần cấp HSK — F06.08; M05 cần tra từ khi Hover — F05.02)."""

from __future__ import annotations

from app.modules.dictionary.application.use_cases.find_entry_ids import FindEntryIdsUseCase
from app.modules.dictionary.application.use_cases.lookup_word import LookupWordUseCase
from app.modules.dictionary.domain.difficulty import example_difficulty
from app.modules.dictionary.domain.entities import (
    DictEntry,
    LookupResult,
    SharedComponent,
    TatoebaExample,
    TermSample,
)
from app.modules.dictionary.domain.hsk import HskInfo, HskSource, resolve_hsk

__all__ = [
    "DictEntry",
    "FindEntryIdsUseCase",
    "HskInfo",
    "HskSource",
    "LookupResult",
    "LookupWordUseCase",
    "SharedComponent",
    "TatoebaExample",
    "TermSample",
    "example_difficulty",
    "resolve_hsk",
]
