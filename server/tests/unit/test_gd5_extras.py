"""GĐ5 bổ sung (unit): Flashcard AI F08.11, gợi ý truyện F10.04, độ phủ F10.05, giọng TTS M11, cỡ chữ F02.04,
lưu hàng loạt F07.12. Dịch vụ ngoài luôn mock."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar

import httpx
import pytest
from pydantic import SecretStr

from app.core.ai_policy import StaticAiPolicy
from app.core.errors import ExternalServiceError, InvalidInputError
from app.core.llm_gemini import LlmCall
from app.core.single_flight import SingleFlight
from app.core.ttl_cache import TtlCache
from app.modules.review.application.dto import AiNoteRequest, EntryFace
from app.modules.review.application.use_cases.get_ai_note import AiNoteConfig, GetAiNoteUseCase
from app.modules.review.domain.ai_note import (
    AiExample,
    AiNote,
    AiNoteContent,
    AiNoteSource,
    AiPhrase,
    CharParts,
    allowed_mnemonic_chars,
    build_mnemonic,
    example_difficulty_cap,
    merge_examples,
    parse_llm_examples,
    parse_llm_phrases,
    sanitize_mnemonic,
)
from app.modules.review.domain.errors import (
    AiNoteEntryNotFoundError,
    AiNoteGeneratorUnavailableError,
    AiNoteRegenerateLimitError,
)
from app.modules.review.infrastructure.gemini_ai_note import GeminiAiNoteGenerator, build_prompt
from app.modules.settings.domain.entities import UserSettings, apply_changes
from app.modules.suggestions.application.dto import SeriesRecommendations
from app.modules.suggestions.application.use_cases.get_chapter_coverage import GetChapterCoverageUseCase
from app.modules.suggestions.application.use_cases.recommend_series import RecommendSeriesUseCase
from app.modules.suggestions.domain.entities import SeriesCandidate
from app.modules.suggestions.domain.rules import (
    coverage_percent,
    coverage_status,
    level_window,
    recommend_series,
)
from app.modules.tts.application.use_cases.list_voices import ListVoicesUseCase
from app.modules.tts.domain.errors import TtsUnavailableError
from app.modules.tts.domain.rules import resolve_voice
from app.modules.tts.domain.voices import DEFAULT_VOICES, make_voice, voices_from_service
from app.modules.vocab.application.use_cases.save_all_page_words import _is_common_single_char
from app.modules.vocab.domain.rules import collect_page_words, pinyin_of_tokens
from tests.conftest import FixedClock
from tests.unit.review_fakes import identity

NOW = datetime(2026, 10, 25, 8, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- F02.04
def test_bubble_font_scale_accepts_only_multiples_of_ten_between_80_and_160() -> None:
    """US-NH-74: 80, 90, ..., 160; mặc định 100."""
    settings = UserSettings(user_id=1)
    assert settings.bubble_font_scale == 100
    for value in range(80, 161, 10):
        apply_changes(settings, {"bubble_font_scale": value})
        assert settings.bubble_font_scale == value
    for bad in (75, 85, 70, 170, 0, -10, "100", True, None, 100.0):
        with pytest.raises(InvalidInputError):
            apply_changes(settings, {"bubble_font_scale": bad})
    assert settings.bubble_font_scale == 160


# --------------------------------------------------------------------------- F07.11, F07.12
def test_pinyin_of_tokens_joins_han_tokens_and_falls_back_to_bubble_pinyin() -> None:
    tokens = [
        {"word": "你好", "pinyin": "nǐ hǎo"},
        {"word": "，", "pinyin": ","},
        {"word": "吗", "pinyin": "ma"},
    ]
    assert pinyin_of_tokens(tokens, "x") == "nǐ hǎo ma"
    assert pinyin_of_tokens([], "nǐ hǎo ma") == "nǐ hǎo ma"
    assert pinyin_of_tokens([{"word": "abc"}], None) is None


def test_collect_page_words_keeps_reading_order_first_bubble_and_only_han_words() -> None:
    """F07.12: gộp từ trùng về bong bóng đầu tiên (theo thứ tự đọc); bỏ dấu câu, số, chữ Latinh."""
    bubbles = [
        (12, 1, [{"word": "学习"}, {"word": "朋友"}, {"word": "abc"}]),
        (11, 0, [{"word": "你好"}, {"word": "学习"}, {"word": "，"}, {"word": "1"}, "rác", {"word": 5}]),
    ]
    assert collect_page_words(bubbles) == [("你好", 11), ("学习", 11), ("朋友", 12)]


# --------------------------------------------------------------------------- M11
def test_voices_from_service_keep_chinese_voices_and_build_vietnamese_names() -> None:
    raw = [
        {"ShortName": "zh-CN-XiaoxiaoNeural", "Locale": "zh-CN", "Gender": "Female"},
        {"ShortName": "zh-TW-YunJheNeural", "Locale": "zh-TW", "Gender": "Male"},
        {"ShortName": "en-US-JennyNeural", "Locale": "en-US", "Gender": "Female"},
        {"ShortName": "zh-CN-Broken", "Locale": "zh-CN"},  # thiếu Gender: bỏ qua
        {"Locale": "zh-CN", "Gender": "Male"},
    ]
    voices = voices_from_service(raw)
    assert [v.short_name for v in voices] == ["zh-CN-XiaoxiaoNeural", "zh-TW-YunJheNeural"]
    assert voices[0].friendly_name == "Xiaoxiao (giọng nữ, Trung Quốc đại lục)"
    assert voices[1].friendly_name == "YunJhe (giọng nam, Đài Loan)"
    assert len(DEFAULT_VOICES) >= 10 and all(v.locale.startswith("zh-") for v in DEFAULT_VOICES)


def test_resolve_voice_accepts_other_chinese_neural_voices_from_the_service_list() -> None:
    assert resolve_voice("zh-CN-XiaochenMultilingualNeural", None) == (
        "zh-CN-XiaochenMultilingualNeural",
        False,
    )
    assert resolve_voice("en-US-JennyNeural", None)[1] is True
    assert resolve_voice("zh-CN-evil; DROP", None)[1] is True


class _Catalog:
    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    async def list_voices(self) -> Any:
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


async def test_list_voices_caches_service_result_and_falls_back_on_failure_or_empty() -> None:
    clock = FixedClock(NOW)
    voice = make_voice("zh-CN-XiaoxiaoNeural", "zh-CN", "Female")
    catalog = _Catalog([voice])
    use_case = ListVoicesUseCase(catalog, TtlCache(clock), clock)
    first = await use_case.execute()
    assert (first.source, first.voices) == ("service", [voice])
    await use_case.execute()
    assert catalog.calls == 1  # lần hai lấy từ bộ đệm

    failing = _Catalog(TtsUnavailableError(), [voice])
    cache: TtlCache[Any] = TtlCache(clock)
    flaky = ListVoicesUseCase(failing, cache, clock)
    down = await flaky.execute()
    assert down.source == "default" and down.voices == list(DEFAULT_VOICES)
    await flaky.execute()
    assert failing.calls == 1  # nhớ tạm, không gọi dồn dập khi dịch vụ lỗi
    clock.at = NOW + timedelta(minutes=6)
    assert (await flaky.execute()).source == "service"  # hết hạn nhớ tạm → gọi lại

    empty = ListVoicesUseCase(_Catalog([]), TtlCache(clock), clock)
    assert (await empty.execute()).source == "default"


def test_ttl_cache_expires() -> None:
    clock = FixedClock(NOW)
    cache: TtlCache[int] = TtlCache(clock)
    assert cache.get() is None
    cache.set(7, timedelta(seconds=10))
    assert cache.get() == 7
    clock.at = NOW + timedelta(seconds=10)
    assert cache.get() is None


# --------------------------------------------------------------------------- F10.04
def _series(
    series_id: int,
    level: int | None,
    rating: float | None = 4.0,
    *,
    in_library: bool = False,
    finished: bool = False,
    library_count: int = 0,
) -> SeriesCandidate:
    return SeriesCandidate(
        series_id, f"Truyện {series_id}", None, None, level, ("tu tiên",), rating, 3, 5, library_count,
        in_library, finished,
    )  # fmt: skip


def test_level_window_is_level_to_level_plus_one_or_low_levels_when_undeclared() -> None:
    assert level_window(3) == (3, 4) and level_window(None) == (1, 3)


def test_recommend_series_orders_by_unseen_then_rating_and_limits_to_three() -> None:
    """US-NH-72: chưa thêm/chưa đọc xong trước, rồi điểm đánh giá; chỉ cấp n và n+1; tối đa theo limit."""
    candidates = [
        _series(1, 3, 5.0, in_library=True),
        _series(2, 3, 3.5),
        _series(3, 4, 4.5),
        _series(4, 5, 5.0),  # ngoài cửa sổ cấp
        _series(5, 4, 4.8, finished=True),
        _series(6, None, 5.0),  # chưa có cấp ước tính
        _series(7, 3, 4.0),
    ]
    picked = recommend_series(candidates, 3, 3)
    assert [r.candidate.series_id for r in picked] == [3, 7, 2]
    everything = recommend_series(candidates, 3, 10)
    assert [r.candidate.series_id for r in everything] == [3, 7, 2, 1, 5]  # truyện đã có/đã đọc xếp sau
    assert "đã có trong Thư viện" in everything[3].reason and "đọc xong" in everything[4].reason
    assert "Đúng trình độ HSK 3" in picked[1].reason and "HSK 4" in picked[0].reason
    assert recommend_series(candidates, 3, 0) == []
    assert recommend_series([_series(9, 8)], 3, 3) == []


def test_recommend_series_without_level_prefers_popular_low_level_series() -> None:
    candidates = [
        _series(1, 2, 5.0, library_count=1),
        _series(2, 1, 3.0, library_count=9),
        _series(3, 6, 5.0),
    ]
    assert [r.candidate.series_id for r in recommend_series(candidates, None, 3)] == [2, 1]


class _SeriesSource:
    def __init__(self, rows: list[SeriesCandidate]) -> None:
        self.rows = rows
        self.window: tuple[int, int] | None = None

    async def candidates(self, identity: Any, hsk_min: int, hsk_max: int) -> list[SeriesCandidate]:
        self.window = (hsk_min, hsk_max)
        return self.rows


class _Level:
    def __init__(self, level: int | None) -> None:
        self.level = level

    async def hsk_level_of(self, user_id: int) -> int | None:
        return self.level


async def test_recommend_use_case_reports_missing_level_and_queries_the_right_window() -> None:
    source = _SeriesSource([_series(1, 2)])
    result: SeriesRecommendations = await RecommendSeriesUseCase(source, _Level(None)).execute(identity(1), 3)
    assert result.hsk_level is None and source.window == (1, 3) and len(result.items) == 1
    declared = await RecommendSeriesUseCase(source, _Level(2)).execute(identity(1), 3)
    assert declared.hsk_level == 2 and source.window == (2, 3)


# --------------------------------------------------------------------------- F10.05
def test_coverage_percent_and_status() -> None:
    assert coverage_percent(1, 3) == 33 and coverage_percent(2, 3) == 67 and coverage_percent(0, 0) == 0
    assert coverage_status(False, 5) == "ready" and coverage_status(True, 5) == "processing"
    assert coverage_status(True, 0) == "empty" and coverage_status(False, 0) == "empty"


class _Chapters:
    def __init__(self, pages: list[Any]) -> None:
        self.pages = pages

    async def pages_of(self, identity: Any, chapter_id: int) -> list[Any]:
        return self.pages


class _Bubbles:
    async def list_by_translation(self, translation_id: int) -> list[Any]:
        from app.modules.imaging.domain.entities import Bubble

        tokens = [{"word": w} for w in ("学习", "朋友", "龘龘", "你好", "，")]
        return [Bubble(1, translation_id, 0, "speech_bubble", 0, 0, 1, 1, "x", tokens=tokens)]


class _CoverageUow:
    def __init__(self, saved: set[str]) -> None:
        self.bubbles = _Bubbles()
        self.saved = self
        self._saved = saved

    async def saved_terms(self, user_id: int, terms: Any) -> set[str]:
        return self._saved & set(terms)

    async def __aenter__(self) -> _CoverageUow:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None


class _Hints:
    LEVELS: ClassVar[dict[str, int | None]] = {"学习": 1, "朋友": 2, "你好": 1, "龘龘": None}

    async def hsk_levels(self, terms: Any) -> dict[str, int | None]:
        return {t: self.LEVELS.get(t) for t in terms}


def _coverage(level: int | None, saved: set[str], status: str = "done") -> GetChapterCoverageUseCase:
    from app.modules.suggestions.application.ports import ChapterPage

    uow = _CoverageUow(saved)
    pages = [ChapterPage(1, 1, 1, "done")] if status != "queued" else []
    pages.append(ChapterPage(2, 2, 2, status if status != "done" else "done"))
    chapters = _Chapters(pages)
    return GetChapterCoverageUseCase(lambda: uow, chapters, _Hints(), _Level(level))  # type: ignore[arg-type]


async def test_coverage_counts_words_up_to_level_and_saved_words_of_any_status() -> None:
    """US-NH-73: Y = từ có cấp 1..n; X = số từ đã có trong sổ tay; từ ngoài HSK không tính."""
    result = await _coverage(1, {"学习"}).execute(identity(1), 7)
    assert (result.known_terms, result.total_terms, result.percent, result.hsk_level) == (1, 2, 50, 1)
    assert result.status == "ready"
    wider = await _coverage(2, {"学习", "朋友"}).execute(identity(1), 7)
    assert (wider.known_terms, wider.total_terms, wider.percent) == (2, 3, 67)


async def test_coverage_without_level_uses_every_leveled_word_and_marks_processing_or_empty() -> None:
    result = await _coverage(None, set()).execute(identity(1), 7)
    assert result.hsk_level is None and result.total_terms == 3 and result.status == "ready"
    processing = await _coverage(None, set(), status="running").execute(identity(1), 7)
    assert processing.status == "processing"  # còn trang chưa xong: tạm tính nhưng vẫn có số liệu
    nothing = await _coverage(None, set(), status="queued").execute(identity(1), 7)
    assert nothing.status == "empty" and nothing.total_terms == 0 and nothing.percent == 0


# --------------------------------------------------------------------------- F08.11 domain
def test_ai_note_content_round_trips_through_json_and_ignores_broken_items() -> None:
    content = AiNoteContent(
        (AiExample("我学习汉语", "wǒ xué xí hàn yǔ", "Tôi học tiếng Trung"),),
        "gồm 子",
        (AiPhrase("学习汉语"),),
    )
    assert AiNoteContent.from_json(content.to_json()) == content
    broken = AiNoteContent.from_json(
        {"examples": [{"zh": 1}, "x", {"zh": "好"}], "mnemonic": 5, "phrases": None}
    )
    assert broken == AiNoteContent((AiExample("好"),), None, ())


def test_parse_llm_examples_and_phrases_require_the_term_and_drop_duplicates() -> None:
    payload = {
        "examples": [
            {"zh": "我每天学习汉语", "pinyin": "p", "vi": "v"},
            {"zh": "我喜欢读书", "pinyin": "p", "vi": "v"},  # không chứa từ
            {"zh": "我每天学习汉语", "pinyin": "p", "vi": "v"},  # trùng
            {"zh": "", "pinyin": "p", "vi": "v"},
            {"pinyin": "p"},
        ],
        "phrases": [{"zh": "学习汉语", "pinyin": "p", "vi": "v"}, {"zh": "读书"}, {"zh": "好好学习"}]
        + [{"zh": f"学习{i}"} for i in range(5)],
    }
    assert [e.zh for e in parse_llm_examples(payload, "学习")] == ["我每天学习汉语"]
    phrases = parse_llm_phrases(payload, "学习")
    assert [p.zh for p in phrases] == ["学习汉语", "好好学习", "学习0"]  # tối đa 3, bỏ cụm không chứa từ
    assert parse_llm_examples("rác", "学习") == [] and parse_llm_phrases(None, "学习") == []


def test_mnemonic_is_built_from_data_and_llm_mnemonic_is_checked_against_it() -> None:
    parts = [CharParts("学", "học", "子", ("冖", "子")), CharParts("习", None, None, ())]
    built = build_mnemonic(parts)
    assert built is not None and "学 (âm Hán Việt: học) gồm 冖 + 子, bộ 子" in built and "习" not in built
    assert build_mnemonic([CharParts("习")]) is None
    allowed = allowed_mnemonic_chars("学习", parts)
    assert {"学", "习", "冖", "子"} == set(allowed)
    ok = "Chữ 学 có 冖 phía trên và 子 phía dưới."
    assert sanitize_mnemonic(ok, allowed, built) == ok
    assert sanitize_mnemonic("Chữ 学 có bộ 木 và 子.", allowed, built) == built  # 木 không có trong dữ liệu
    assert sanitize_mnemonic(5, allowed, built) == built and sanitize_mnemonic(ok, frozenset(), built) is None


def test_example_cap_and_merge_examples_top_up_from_fallback() -> None:
    assert example_difficulty_cap(3, 5) == 4 and example_difficulty_cap(None, 2) == 3
    assert example_difficulty_cap(None, None) == 2
    llm, fallback = [AiExample("甲1")], [AiExample("甲1"), AiExample("乙2"), AiExample("丙3")]
    assert [e.zh for e in merge_examples(llm, fallback)] == ["甲1", "乙2"]
    assert [e.zh for e in merge_examples([], fallback)] == ["甲1", "乙2"]


# --------------------------------------------------------------------------- F08.11 use case
class _Vocab:
    def __init__(self, faces: dict[int, EntryFace]) -> None:
        self.faces_by_id = faces

    async def faces(self, user_id: int, entry_ids: Any) -> dict[int, EntryFace]:
        return {i: self.faces_by_id[i] for i in entry_ids if i in self.faces_by_id}


class _Notes:
    def __init__(self) -> None:
        self.items: dict[int, AiNote] = {}
        self.llm_today = 0

    async def get(self, entry_id: int) -> AiNote | None:
        return self.items.get(entry_id)

    async def save(self, note: AiNote) -> None:
        self.items[note.vocab_entry_id] = note

    async def count_llm_between(self, user_id: int, start: datetime, end: datetime) -> int:
        return self.llm_today


class _NoteUow:
    def __init__(self, faces: dict[int, EntryFace], notes: _Notes) -> None:
        self.vocab = _Vocab(faces)
        self.ai_notes = notes

    async def __aenter__(self) -> _NoteUow:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None

    async def commit(self) -> None:
        return None


class _Generator:
    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[AiNoteRequest] = []

    async def generate(self, request: AiNoteRequest) -> object:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _Knowledge:
    async def char_parts(self, term: str) -> list[CharParts]:
        return [CharParts("学", "học", "子", ("冖", "子")), CharParts("习", "tập", "羽", ("羽",))]

    async def examples(self, term: str, max_difficulty: int, limit: int) -> list[AiExample]:
        return [
            AiExample("他在学习汉语", "p1", "Anh ấy học tiếng Trung"),
            AiExample("学习很有趣", "p2", "Học rất vui"),
        ]

    async def collocations(self, term: str, limit: int) -> list[AiPhrase]:
        return [
            AiPhrase("学习汉语", "xué xí hàn yǔ", "học tiếng Trung"),
            AiPhrase("努力学习", None, "chăm học"),
        ]


class _Levels:
    def __init__(self, level: int | None) -> None:
        self.level = level
        self.seen: list[str] = []

    async def difficulties(self, sentences: Any) -> list[int | None]:
        self.seen.extend(sentences)
        return [self.level for _ in sentences]


class _Profiles:
    async def profile_of(self, user_id: int) -> tuple[int | None, str | None]:
        return 2, "UTC"


FACE = EntryFace(1, "学习", "xué xí", "học tập; học", "học tập", None, "learning", False, 1, None)
GOOD = {
    "examples": [
        {"zh": "我喜欢学习中文", "pinyin": "p", "vi": "Tôi thích học tiếng Trung"},
        {"zh": "学习让我快乐", "pinyin": "p", "vi": "Học khiến tôi vui"},
    ],
    "mnemonic": "Chữ 学 có 冖 che 子 như đứa trẻ đang học.",
    "phrases": [{"zh": "学习汉语", "pinyin": "p", "vi": "v"}, {"zh": "好好学习", "pinyin": "p", "vi": "v"}],
}


class _Env:
    def __init__(
        self,
        *outcomes: Any,
        enabled: bool = True,
        level: int | None = 2,
        daily_limit: int = 20,
        faces: dict[int, EntryFace] | None = None,
    ) -> None:
        self.notes = _Notes()
        self.generator = _Generator(*outcomes)
        self.levels = _Levels(level)
        uow = _NoteUow(faces if faces is not None else {1: FACE}, self.notes)
        self.use_case = GetAiNoteUseCase(
            lambda: uow,  # type: ignore[arg-type,return-value]
            self.generator,
            _Knowledge(),
            self.levels,
            _Profiles(),
            SingleFlight(),
            AiNoteConfig(3, 5.0, "gemini-test"),
            StaticAiPolicy(enabled, daily_limit),
            FixedClock(NOW),
        )


async def test_ai_note_uses_llm_content_after_validation_and_caches_it() -> None:
    env = _Env(GOOD)
    view = await env.use_case.execute(identity(1), 1)
    note = view.note
    assert note.source is AiNoteSource.LLM and note.model == "gemini-test" and note.regenerate_count == 0
    assert [e.zh for e in note.content.examples] == ["我喜欢学习中文", "学习让我快乐"]
    assert note.content.mnemonic == GOOD["mnemonic"]
    assert [p.zh for p in note.content.phrases] == ["学习汉语", "好好学习"]
    assert view.regenerate_remaining == 3
    sent = env.generator.requests[0]  # chỉ từ, pinyin, nghĩa, cấp HSK, trình độ, dữ liệu chiết tự
    assert (sent.term, sent.pinyin, sent.hsk_level, sent.learner_level) == ("学习", "xué xí", 1, 2)
    again = await env.use_case.execute(identity(1), 1)
    assert again.note.generated_at == note.generated_at and len(env.generator.requests) == 1  # bộ đệm


async def test_ai_note_replaces_mnemonic_with_foreign_component_by_data_built_version() -> None:
    bad = {**GOOD, "mnemonic": "Chữ 学 có bộ 木 ở trên."}
    note = (await _Env(bad).use_case.execute(identity(1), 1)).note
    assert note.source is AiNoteSource.LLM
    assert note.content.mnemonic is not None and "木" not in note.content.mnemonic
    assert "冖 + 子" in note.content.mnemonic


async def test_ai_note_drops_examples_too_hard_or_missing_term_and_tops_up_from_dictionary() -> None:
    env = _Env(GOOD, level=6)  # độ khó 6 > trình độ 2 + 1 → mọi câu LLM bị loại
    note = (await env.use_case.execute(identity(1), 1)).note
    assert note.source is AiNoteSource.FALLBACK and note.model is None
    assert [e.zh for e in note.content.examples] == ["他在学习汉语", "学习很有趣"]
    assert env.levels.seen == ["我喜欢学习中文", "学习让我快乐"]

    partial = {**GOOD, "examples": [{"zh": "我喜欢学习中文", "pinyin": "p", "vi": "v"}]}
    topped = (await _Env(partial).use_case.execute(identity(1), 1)).note
    assert topped.source is AiNoteSource.LLM
    assert [e.zh for e in topped.content.examples] == ["我喜欢学习中文", "他在学习汉语"]  # bù câu thứ hai

    no_phrases = {**GOOD, "phrases": []}
    bumped = (await _Env(no_phrases).use_case.execute(identity(1), 1)).note
    assert [p.zh for p in bumped.content.phrases] == ["学习汉语", "努力学习"]  # bù cụm từ từ từ điển


@pytest.mark.parametrize(
    "outcome",
    [
        AiNoteGeneratorUnavailableError("timeout"),
        RuntimeError("lỗi lạ của adapter"),
        None,
        "không phải JSON object",
        {"examples": "sai kiểu"},
    ],
)
async def test_ai_note_falls_back_without_raising_when_llm_fails_or_returns_garbage(outcome: Any) -> None:
    view = await _Env(outcome).use_case.execute(identity(1), 1)
    assert view.note.source is AiNoteSource.FALLBACK
    assert view.note.content.mnemonic is not None and view.note.content.phrases


async def test_ai_note_skips_llm_when_disabled_or_daily_limit_reached() -> None:
    disabled = _Env(enabled=False)
    assert (await disabled.use_case.execute(identity(1), 1)).note.source is AiNoteSource.FALLBACK
    assert disabled.generator.requests == []
    limited = _Env(GOOD, daily_limit=2)
    limited.notes.llm_today = 2
    assert (await limited.use_case.execute(identity(1), 1)).note.source is AiNoteSource.FALLBACK
    assert limited.generator.requests == []


async def test_ai_note_regenerate_counts_is_limited_and_unknown_entry_is_not_found() -> None:
    env = _Env(GOOD, GOOD, GOOD, GOOD)
    await env.use_case.execute(identity(1), 1)
    for expected in (1, 2, 3):
        view = await env.use_case.execute(identity(1), 1, regenerate=True)
        assert view.note.regenerate_count == expected
    with pytest.raises(AiNoteRegenerateLimitError):
        await env.use_case.execute(identity(1), 1, regenerate=True)
    assert len(env.generator.requests) == 4  # lần bị từ chối không gọi LLM
    with pytest.raises(AiNoteEntryNotFoundError):
        await env.use_case.execute(identity(2), 99)
    # Tạo lại khi chưa có bản nào thì như tạo lần đầu, không tính lượt.
    fresh = await _Env(GOOD).use_case.execute(identity(1), 1, regenerate=True)
    assert fresh.note.regenerate_count == 0


# --------------------------------------------------------------------------- F08.11 adapter Gemini
def _gemini_body(payload: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False)
    return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}]}


async def test_gemini_ai_note_sends_only_word_data_logs_the_call_and_maps_errors() -> None:
    requests: list[httpx.Request] = []
    calls: list[LlmCall] = []

    async def record(call: LlmCall) -> None:
        calls.append(call)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_gemini_body(GOOD))

    generator = GeminiAiNoteGenerator(
        SecretStr("AIza-secret"), "gemini-test", 5.0, record, transport=httpx.MockTransport(handler)
    )
    request = AiNoteRequest("学习", "xué xí", "học tập", 1, 2, (CharParts("学", "học", "子", ("冖", "子")),))
    assert await generator.generate(request) == GOOD
    sent = requests[0]
    assert sent.headers["x-goog-api-key"] == "AIza-secret" and b"AIza" not in sent.url.raw_path
    prompt = json.loads(sent.content)["contents"][0]["parts"][0]["text"]
    assert "学习" in prompt and "xué xí" in prompt and "HSK 2" in prompt and "HSK 3 trở xuống" in prompt
    assert "冖 + 子" in prompt and "bộ 子" in prompt and "@" not in prompt and "AIza" not in prompt
    assert [(c.operation, c.status) for c in calls] == [("ai_note", "ok")]

    down = GeminiAiNoteGenerator(
        SecretStr("k"),
        "m",
        5.0,
        record,
        transport=httpx.MockTransport(lambda r: httpx.Response(403)),
    )
    with pytest.raises(AiNoteGeneratorUnavailableError):
        await down.generate(request)
    assert "chưa xác định" in build_prompt(AiNoteRequest("学习", None, None, None, None))


def test_external_service_error_type_is_not_leaked_by_ai_note_errors() -> None:
    """Lỗi của port không phải DomainError nên không bao giờ thành phản hồi API (F08.11)."""
    assert not issubclass(AiNoteGeneratorUnavailableError, ExternalServiceError)


def test_save_all_skips_only_common_single_characters() -> None:
    """F07.12: lưu cả trang chỉ bỏ 是, 吗…; 什么, 看看, 你好 vẫn lưu (người dùng chốt 25/10/2026)."""
    assert all(_is_common_single_char(t) for t in ("是", "吗", "的", "了"))
    assert not any(_is_common_single_char(t) for t in ("什么", "看看", "你好", "看", "学习"))
