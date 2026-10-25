from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.dictionary.domain.entities import (
    CharacterBreakdown,
    Example,
    ImportReport,
    LookupResult,
    Reading,
    SearchHit,
    SearchPage,
    Token,
    WordOfTheDay,
)
from app.modules.dictionary.domain.hsk import HskInfo
from app.modules.dictionary.domain.pos import pos_labels


class HskResponse(BaseModel):
    level: int | None = Field(description="1–9; 7 là nhóm 7–9 của HSK 3.0; null = Ngoài HSK")
    source: str = Field(
        description="list: có trong danh sách · derived: suy từ chữ cấu thành · none: Ngoài HSK"
    )

    @classmethod
    def from_info(cls, info: HskInfo) -> HskResponse:
        return cls(level=info.level, source=info.source.value)


class ExampleResponse(BaseModel):
    zh: str
    pinyin: str | None
    vi: str | None
    source: str

    @classmethod
    def from_entity(cls, e: Example) -> ExampleResponse:
        return cls(zh=e.zh, pinyin=e.pinyin, vi=e.vi, source=e.source)


class DefinitionResponse(BaseModel):
    source: str
    gloss: str


class ReadingResponse(BaseModel):
    pinyin: str
    han_viet: str | None
    part_of_speech: list[str]
    definitions: list[DefinitionResponse]
    english: list[str]
    examples: list[ExampleResponse]

    @classmethod
    def from_entity(cls, r: Reading) -> ReadingResponse:
        return cls(
            pinyin=r.pinyin,
            han_viet=r.han_viet,
            part_of_speech=list(pos_labels(r.part_of_speech)),
            definitions=[DefinitionResponse(source=d.source, gloss=d.gloss) for d in r.definitions],
            english=list(r.english),
            examples=[ExampleResponse.from_entity(e) for e in r.examples],
        )


class EtymologyResponse(BaseModel):
    type: str | None = None
    hint: str | None = None
    phonetic: str | None = None
    semantic: str | None = None


class CharacterResponse(BaseModel):
    ch: str
    found: bool
    pinyin: str | None = None
    han_viet: str | None = None
    radical: str | None = None
    stroke_count: int | None = None
    decomposition: str | None = None
    components: list[str] = []
    definition_en: str | None = None
    strokes: list[str] = []
    medians: list[list[list[int]]] = []
    etymology: EtymologyResponse | None = None

    @classmethod
    def from_entity(cls, c: CharacterBreakdown) -> CharacterResponse:
        if c.info is None:
            return cls(ch=c.ch, found=False)
        i = c.info
        return cls(
            ch=c.ch,
            found=True,
            pinyin=i.pinyin,
            han_viet=i.han_viet,
            radical=i.radical,
            stroke_count=i.stroke_count,
            decomposition=i.decomposition,
            components=list(i.components),
            definition_en=i.definition_en,
            strokes=list(i.stroke_data.strokes) if i.stroke_data else [],
            medians=[[[x, y] for x, y in m] for m in i.stroke_data.medians] if i.stroke_data else [],
            etymology=EtymologyResponse(
                type=i.etymology.type,
                hint=i.etymology.hint,
                phonetic=i.etymology.phonetic,
                semantic=i.etymology.semantic,
            )
            if i.etymology
            else None,
        )


class SpecializedResponse(BaseModel):
    kind: str
    label: str
    meanings: list[str]


class LookupResponse(BaseModel):
    term: str
    found: bool
    pinyin: str | None
    han_viet: str | None
    hsk: HskResponse
    readings: list[ReadingResponse]
    specialized: list[SpecializedResponse]
    characters: list[CharacterResponse]
    limited: bool = Field(description="true: Khách chỉ thấy phần cơ bản, cần đăng nhập để xem đầy đủ")

    @classmethod
    def from_result(cls, r: LookupResult) -> LookupResponse:
        return cls(
            term=r.term,
            found=r.found,
            pinyin=r.pinyin,
            han_viet=r.han_viet,
            hsk=HskResponse.from_info(r.hsk),
            readings=[ReadingResponse.from_entity(x) for x in r.readings],
            specialized=[
                SpecializedResponse(
                    kind=s.kind,
                    label="Tên riêng (từ điển tu tiên)" if s.kind == "name" else "Từ điển tu tiên",
                    meanings=list(s.meanings),
                )
                for s in r.specialized
            ],
            characters=[CharacterResponse.from_entity(c) for c in r.characters],
            limited=r.limited,
        )


class SearchHitResponse(BaseModel):
    term: str
    pinyin: str
    han_viet: str | None
    preview: str | None
    hsk_level: int | None

    @classmethod
    def from_entity(cls, h: SearchHit) -> SearchHitResponse:
        return cls(
            term=h.simplified, pinyin=h.pinyin, han_viet=h.han_viet, preview=h.preview, hsk_level=h.hsk_level
        )


class SearchPageResponse(BaseModel):
    items: list[SearchHitResponse]
    total: int
    page: int
    size: int

    @classmethod
    def from_page(cls, p: SearchPage) -> SearchPageResponse:
        return cls(
            items=[SearchHitResponse.from_entity(h) for h in p.items], total=p.total, page=p.page, size=p.size
        )


class SegmentRequest(BaseModel):
    text: str = Field(max_length=1000)


class TokenResponse(BaseModel):
    text: str
    pinyin: str | None
    lookupable: bool

    @classmethod
    def from_entity(cls, t: Token) -> TokenResponse:
        return cls(text=t.text, pinyin=t.pinyin, lookupable=t.lookupable)


class SegmentResponse(BaseModel):
    tokens: list[TokenResponse]


class CharactersResponse(BaseModel):
    characters: list[CharacterResponse]


class WordOfTheDayResponse(BaseModel):
    term: str
    pinyin: str
    han_viet: str | None
    meaning: str
    hsk_level: int
    example: ExampleResponse | None

    @classmethod
    def from_entity(cls, w: WordOfTheDay) -> WordOfTheDayResponse:
        return cls(
            term=w.term,
            pinyin=w.pinyin,
            han_viet=w.han_viet,
            meaning=w.meaning,
            hsk_level=w.hsk_level,
            example=ExampleResponse.from_entity(w.example) if w.example else None,
        )


class ImportReportResponse(BaseModel):
    added: int
    updated: int
    skipped: int
    rejected_count: int
    rejected: list[str] = Field(description="Tối đa 100 dòng bị bỏ qua đầu tiên")
    per_level: dict[int, int]

    @classmethod
    def from_report(cls, r: ImportReport) -> ImportReportResponse:
        return cls(
            added=r.added,
            updated=r.updated,
            skipped=r.skipped,
            rejected_count=len(r.rejected),
            rejected=list(r.rejected)[:100],
            per_level=dict(r.per_level),
        )
