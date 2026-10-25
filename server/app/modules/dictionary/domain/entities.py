from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from app.modules.dictionary.domain.hsk import HskInfo


@dataclass(frozen=True, slots=True)
class Definition:
    source: str  # thienchuu | cvdict
    gloss: str


@dataclass(frozen=True, slots=True)
class Example:
    zh: str
    pinyin: str | None
    vi: str | None
    source: str


@dataclass(frozen=True, slots=True)
class DictEntry:
    id: int
    simplified: str
    traditional: str | None
    pinyin: str
    pinyin_numeric: str
    han_viet: str | None
    definitions: tuple[Definition, ...]
    english: tuple[str, ...]
    part_of_speech: str | None
    source: str
    freq_rank: int | None = None


@dataclass(frozen=True, slots=True)
class StrokeData:
    """Nét viết kiểu makemeahanzi: `strokes[i]` là viền SVG, `medians[i]` là đường chạy bút của nét i."""

    strokes: tuple[str, ...]
    medians: tuple[tuple[tuple[int, int], ...], ...]


@dataclass(frozen=True, slots=True)
class EtymologyInfo:
    type: str | None
    hint: str | None
    phonetic: str | None
    semantic: str | None


@dataclass(frozen=True, slots=True)
class HanziInfo:
    ch: str
    pinyin: str | None
    han_viet: str | None
    radical: str | None
    stroke_count: int | None
    decomposition: str | None
    components: tuple[str, ...]
    definition_en: str | None
    stroke_data: StrokeData | None = None
    etymology: EtymologyInfo | None = None


@dataclass(frozen=True, slots=True)
class CharacterBreakdown:
    """Phân rã một chữ; `info` rỗng nghĩa là "Chưa có dữ liệu phân rã"."""

    ch: str
    info: HanziInfo | None


@dataclass(frozen=True, slots=True)
class SpecializedMeaning:
    kind: str  # phrase | name
    meanings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Reading:
    """Một cách đọc của từ (vd. 行 háng / xíng) cùng các nghĩa gộp từ mọi nguồn."""

    pinyin: str
    pinyin_numeric: str
    han_viet: str | None
    part_of_speech: str | None
    definitions: tuple[Definition, ...]
    english: tuple[str, ...]
    examples: tuple[Example, ...]


@dataclass(frozen=True, slots=True)
class LookupResult:
    term: str
    found: bool
    pinyin: str | None
    han_viet: str | None
    hsk: HskInfo
    readings: tuple[Reading, ...] = ()
    specialized: tuple[SpecializedMeaning, ...] = ()
    characters: tuple[CharacterBreakdown, ...] = ()
    limited: bool = False  # Khách chỉ thấy phần cơ bản


@dataclass(frozen=True, slots=True)
class SearchHit:
    entry_id: int
    simplified: str
    pinyin: str
    han_viet: str | None
    preview: str | None
    hsk_level: int | None


@dataclass(frozen=True, slots=True)
class SearchPage:
    items: Sequence[SearchHit]
    total: int
    page: int
    size: int


@dataclass(frozen=True, slots=True)
class Token:
    text: str
    pinyin: str | None
    lookupable: bool  # False với số, dấu câu, chữ Latin


@dataclass(frozen=True, slots=True)
class WordOfTheDay:
    term: str
    pinyin: str
    han_viet: str | None
    meaning: str
    hsk_level: int
    example: Example | None


@dataclass(frozen=True, slots=True)
class TermSample:
    """Một từ HSK kèm nghĩa đầu tiên, dùng làm phương án nhiễu cho bài kiểm tra (F09.08)."""

    term: str
    pinyin: str
    meaning_vi: str
    hsk_level: int


@dataclass(frozen=True, slots=True)
class TatoebaExample:
    """Câu ví dụ Tatoeba có mã và độ khó (F09.09)."""

    id: int
    zh: str
    pinyin: str | None
    vi: str | None
    difficulty_level: int | None


@dataclass(frozen=True, slots=True)
class SharedComponent:
    """Chữ `related` có chung thành phần/bộ thủ `component` với chữ `via` (F09.09 nguồn c)."""

    related: str
    via: str
    component: str


@dataclass(frozen=True, slots=True)
class EntryRow:
    """Một dòng dữ liệu từ điển cần nạp (F06.06)."""

    simplified: str
    traditional: str | None
    pinyin: str
    pinyin_numeric: str
    han_viet: str | None
    definitions: tuple[Definition, ...]
    english: tuple[str, ...]
    part_of_speech: str | None
    source: str


@dataclass(frozen=True, slots=True)
class HskRow:
    word: str
    level: int
    pinyin: str | None
    pos: str | None


@dataclass(frozen=True, slots=True)
class ImportReport:
    added: int = 0
    updated: int = 0
    skipped: int = 0
    rejected: Sequence[str] = field(default_factory=tuple)
    per_level: Mapping[int, int] = field(default_factory=dict)
