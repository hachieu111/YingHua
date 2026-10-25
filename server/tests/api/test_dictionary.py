"""M06 Từ điển — F06.01…F06.08 (US-NH-26…30, US-QT-09, US-QT-10).

CSDL kiểm thử không có dữ liệu từ điển thật nên mỗi test tự dựng dữ liệu nhỏ bằng chữ Hán hiếm và xóa đúng
các dòng đó sau khi xong (không TRUNCATE).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, TypeAlias

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.dictionary.domain.pinyin import search_key
from app.modules.dictionary.infrastructure.orm_models import (
    DictEntryModel,
    DictExampleModel,
    HanziModel,
    HskWordModel,
    XianxiaEntryModel,
)
from app.modules.dictionary.infrastructure.public import SqlDictionaryUnitOfWork
from tests.helpers import Account, error_code, make_admin, register

pytestmark = pytest.mark.integration

# Chữ/từ hiếm do test tự chọn: không trùng dữ liệu từ điển thật.
WORD = "鑫淼"  # có 2 cách đọc, 2 nguồn
LONG_WORD = "鑫淼淼"  # chứa WORD; có tên riêng tu tiên
LISTED = "淼淼"  # có trong danh sách HSK nhưng không có mục từ điển
WOTD_WORD = "鑫鑫"  # từ vựng trong ngày (HSK 8, có mục từ điển)
NO_DATA_CHAR = "𠀀"  # U+20000, không có dữ liệu phân rã
TEST_SOURCES = ("test", "test2")

IMPORT_WORDS = ("鑫鑫鑫", "淼淼淼", "鑫鑫鑫鑫", "鑫鑫鑫鑫鑫")
SEED_HSK_WORDS = ("鑫", "淼", LISTED, WOTD_WORD)
SEED_XIANXIA_KEYS = (WORD, LONG_WORD)
BROKEN_CHAR = "垚"  # stroke_data hỏng (medians thiếu)
SEED_HANZI = ("鑫", "淼", BROKEN_CHAR)

Factory: TypeAlias = async_sessionmaker[AsyncSession]


def _entry(
    simplified: str,
    numeric: str,
    glosses: list[str],
    source: str = "test",
    **extra: Any,
) -> DictEntryModel:
    marks = {"xin1 miao3": "xīn miǎo", "xin4 miao4": "xìn miào"}.get(numeric, numeric)
    return DictEntryModel(
        simplified=simplified,
        pinyin=marks,
        pinyin_numeric=numeric,
        pinyin_search=search_key(numeric),
        meanings_vi=[{"src": "cvdict", "gloss": g} for g in glosses],
        meanings_en=[],
        search_vi=" | ".join(glosses).lower(),
        source=source,
        **extra,
    )


async def _purge(factory: Factory) -> None:
    async with factory() as session:
        # Mục từ điển của lần nạp thử (nguồn cvdict) chỉ xóa đúng các từ hiếm của test này.
        await session.execute(
            delete(DictEntryModel).where(
                (DictEntryModel.source.in_(TEST_SOURCES))
                | ((DictEntryModel.source == "cvdict") & DictEntryModel.simplified.in_(IMPORT_WORDS))
            )
        )
        await session.execute(
            delete(HskWordModel).where(HskWordModel.word.in_((*SEED_HSK_WORDS, *IMPORT_WORDS)))
        )
        await session.execute(delete(HanziModel).where(HanziModel.ch.in_(SEED_HANZI)))
        await session.execute(delete(XianxiaEntryModel).where(XianxiaEntryModel.key.in_(SEED_XIANXIA_KEYS)))
        await session.commit()


@pytest.fixture
async def dict_data(app: FastAPI, client: httpx.AsyncClient) -> AsyncIterator[None]:
    """Dựng dữ liệu từ điển nhỏ rồi dọn sạch (dọn cả trước khi dựng, phòng lần chạy trước bị ngắt)."""
    factory: Factory = app.state.container.session_factory
    await _purge(factory)
    async with factory() as session:
        first = _entry(
            WORD,
            "xin1 miao3",
            ["giàu có", "hai", "ba", "bốn"],
            part_of_speech="v,vn",
            han_viet="Hâm Diểu",
            traditional="鑫淼",
        )
        other_reading = _entry(WORD, "xin4 miao4", ["đọc khác"])
        other_source = _entry(WORD, "xin1 miao3", ["thêm một nghĩa", "phồn vinh kỳ diệu"], source="test2")
        long_word = _entry(LONG_WORD, "xin1 miao3 miao3", ["rộng lớn"])
        wotd = _entry(WOTD_WORD, "xin1 xin1", ["ba chữ vàng"])
        session.add_all([first, other_reading, other_source, long_word, wotd])
        await session.flush()
        session.add_all(
            [
                DictExampleModel(entry_id=first.id, zh=f"{WORD}之地很大", vi="Vùng đất rộng", source="gloss"),
                DictExampleModel(entry_id=first.id, zh=WORD, vi=None, source="gloss"),
            ]
        )
        session.add_all(
            [
                HskWordModel(word="鑫", level=4),
                HskWordModel(word="淼", level=2),
                HskWordModel(word=LISTED, level=3),
                HskWordModel(word=WOTD_WORD, level=8),
                HanziModel(
                    ch="鑫",
                    radical="金",
                    stroke_count=24,
                    components=["金"],
                    han_viet="hâm",
                    stroke_data={
                        "strokes": ["M 1 1 L 2 2 Z", "M 3 3 L 4 4 Z"],
                        "medians": [[[1, 2], [3, 4]], [[5, 6], [7, 8]]],
                    },
                    etymology={"type": "pictophonetic", "hint": "gold", "phonetic": "金"},
                ),
                HanziModel(
                    ch=BROKEN_CHAR,
                    radical="土",
                    stroke_count=6,
                    components=["土"],
                    stroke_data={"strokes": ["M 1 1 Z", "M 2 2 Z"], "medians": [[[1, 2], [3, 4]]]},
                ),
                HanziModel(ch="淼", radical="水", stroke_count=11, components=["水"], han_viet="diểu"),
                XianxiaEntryModel(kind="phrase", key=WORD, meanings=["giàu có"]),  # trùng nghĩa thông thường
                XianxiaEntryModel(kind="phrase", key=WORD, meanings=["linh thạch cực phẩm"]),
                XianxiaEntryModel(kind="name", key=LONG_WORD, meanings=["Tân Diểu"]),
            ]
        )
        await session.commit()
    try:
        yield
    finally:
        await _purge(factory)


async def _event_count(app: FastAPI, user_id: int, action: str) -> int:
    async with app.state.container.session_factory() as session:
        value = await session.scalar(
            text("SELECT count(*) FROM lookup_events WHERE user_id = :u AND action = :a"),
            {"u": user_id, "a": action},
        )
    return int(value or 0)


# ---------------------------------------------------------------- lookup (F06.01, US-NH-26)


async def test_lookup_shows_full_detail_to_logged_in_user(client: httpx.AsyncClient, dict_data: None) -> None:
    """US-NH-26: readings gộp theo cách đọc, nghĩa đánh số giữ thứ tự, ví dụ, phân rã, cấp HSK."""
    account = await register(client)
    res = await client.get("/api/v1/dictionary/lookup", params={"term": WORD}, headers=account.headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["found"] and not body["limited"]
    assert body["pinyin"] == "xīn miǎo" and body["han_viet"] == "Hâm Diểu"
    first, second = body["readings"]
    assert first["pinyin"] == "xīn miǎo" and second["pinyin"] == "xìn miào"
    assert [d["gloss"] for d in first["definitions"]] == [
        "giàu có",
        "hai",
        "ba",
        "bốn",
        "thêm một nghĩa",
        "phồn vinh kỳ diệu",
    ]
    assert first["part_of_speech"] == ["động từ", "danh động từ"]
    assert [d["gloss"] for d in second["definitions"]] == ["đọc khác"]
    assert first["examples"][0]["vi"] == "Vùng đất rộng"  # câu có bản dịch lên trước
    assert len(first["examples"]) == 2
    assert [c["ch"] for c in body["characters"]] == ["鑫", "淼"]
    assert body["characters"][0]["radical"] == "金" and body["characters"][0]["found"]
    assert body["hsk"] == {"level": 4, "source": "derived"}


async def test_lookup_hsk_source_list_and_none(client: httpx.AsyncClient, dict_data: None) -> None:
    """F06.08: cấp HSK từ danh sách / suy từ chữ cấu thành / Ngoài HSK."""
    account = await register(client)
    listed = await client.get("/api/v1/dictionary/lookup", params={"term": LISTED}, headers=account.headers)
    assert listed.json()["hsk"] == {"level": 3, "source": "list"}
    none = await client.get(
        "/api/v1/dictionary/lookup", params={"term": NO_DATA_CHAR}, headers=account.headers
    )
    assert none.json()["hsk"] == {"level": None, "source": "none"}


async def test_lookup_guest_sees_only_basics(client: httpx.AsyncClient, dict_data: None) -> None:
    """US-NH-26: Khách chỉ thấy pinyin + tối đa 3 nghĩa, không có ví dụ / phân rã."""
    res = await client.get("/api/v1/dictionary/lookup", params={"term": WORD})
    assert res.status_code == 200
    body = res.json()
    assert body["limited"] is True and body["pinyin"] == "xīn miǎo"
    assert len(body["readings"][0]["definitions"]) == 3
    assert body["readings"][0]["examples"] == []
    assert body["characters"] == [] and body["specialized"] == []
    assert body["han_viet"] is None


async def test_lookup_unknown_word_returns_found_false_with_derived_pinyin(
    client: httpx.AsyncClient, dict_data: None
) -> None:
    """US-NH-26: từ chưa có trong từ điển vẫn có pinyin suy ra."""
    account = await register(client)
    res = await client.get("/api/v1/dictionary/lookup", params={"term": LISTED}, headers=account.headers)
    body = res.json()
    assert res.status_code == 200 and body["found"] is False and body["readings"] == []
    assert body["pinyin"] == "miǎo miǎo"


@pytest.mark.parametrize("term", ["abc", "123", "hello world"])
async def test_lookup_rejects_text_without_han(client: httpx.AsyncClient, term: str) -> None:
    res = await client.get("/api/v1/dictionary/lookup", params={"term": term})
    assert res.status_code == 400 and error_code(res) == "NOT_CHINESE_TEXT"


async def test_lookup_requires_term(client: httpx.AsyncClient) -> None:
    res = await client.get("/api/v1/dictionary/lookup", params={"term": ""})
    assert res.status_code == 422
    assert (await client.get("/api/v1/dictionary/lookup")).status_code == 422


async def test_lookup_records_event_for_logged_in_user_only(
    app: FastAPI, client: httpx.AsyncClient, dict_data: None
) -> None:
    """F06.01: ghi lookup_events cho người đăng nhập, không ghi cho Khách."""
    account = await register(client)
    await client.get("/api/v1/dictionary/lookup", params={"term": WORD}, headers=account.headers)
    await client.get("/api/v1/dictionary/lookup", params={"term": WORD}, headers=account.headers)
    await client.get("/api/v1/dictionary/lookup", params={"term": WORD})
    assert await _event_count(app, account.id, "lookup") == 2


# ---------------------------------------------------------------- tu tiên (F06.03, US-NH-28)


async def test_xianxia_shown_only_when_meaning_differs(client: httpx.AsyncClient, dict_data: None) -> None:
    account = await register(client)
    res = await client.get("/api/v1/dictionary/lookup", params={"term": WORD}, headers=account.headers)
    specialized = res.json()["specialized"]
    assert [s["meanings"] for s in specialized] == [["linh thạch cực phẩm"]]  # nghĩa trùng bị lọc
    assert specialized[0]["kind"] == "phrase"


async def test_xianxia_proper_name_always_shown(client: httpx.AsyncClient, dict_data: None) -> None:
    account = await register(client)
    res = await client.get("/api/v1/dictionary/lookup", params={"term": LONG_WORD}, headers=account.headers)
    specialized = res.json()["specialized"]
    assert [(s["kind"], s["meanings"]) for s in specialized] == [("name", ["Tân Diểu"])]


async def test_xianxia_hidden_when_user_turns_it_off(client: httpx.AsyncClient, dict_data: None) -> None:
    account = await register(client)
    patch = await client.patch("/api/v1/settings", json={"show_xianxia": False}, headers=account.headers)
    assert patch.status_code == 200
    res = await client.get("/api/v1/dictionary/lookup", params={"term": LONG_WORD}, headers=account.headers)
    assert res.json()["specialized"] == []


# ---------------------------------------------------------------- search (F06.02, US-NH-27)


async def _search(client: httpx.AsyncClient, q: str, **params: Any) -> dict[str, Any]:
    res = await client.get("/api/v1/dictionary/search", params={"q": q, **params})
    assert res.status_code == 200, res.text
    body: dict[str, Any] = res.json()
    return body


async def test_search_by_han_puts_exact_match_first_and_merges_sources(
    client: httpx.AsyncClient, dict_data: None
) -> None:
    body = await _search(client, WORD)
    terms = [(i["term"], i["pinyin"]) for i in body["items"]]
    # Cùng chữ + cùng cách đọc (khác nguồn) chỉ ra một kết quả.
    assert terms.count((WORD, "xīn miǎo")) == 1
    assert [t[0] for t in terms] == [WORD, WORD, LONG_WORD]  # khớp chính xác trước, khớp chứa sau
    assert body["total"] == 3 and body["page"] == 1 and body["size"] == 20
    first = body["items"][0]
    assert first["preview"] == "giàu có" and first["han_viet"] == "Hâm Diểu"
    assert first["hsk_level"] is None


@pytest.mark.parametrize("query", ["xinmiao", "xin1miao3", "xin1 miao3", "XINMIAO", "xīnmiǎo"])
async def test_search_by_pinyin_variants(client: httpx.AsyncClient, dict_data: None, query: str) -> None:
    body = await _search(client, query)
    terms = {i["term"] for i in body["items"]}
    assert WORD in terms and LONG_WORD in terms


async def test_search_by_pinyin_with_tone_numbers_is_exact_first(
    client: httpx.AsyncClient, dict_data: None
) -> None:
    body = await _search(client, "xin1miao3")
    assert body["items"][0]["term"] == WORD  # khớp đủ lên trước khớp tiền tố (鑫淼淼)


async def test_search_by_vietnamese_meaning(client: httpx.AsyncClient, dict_data: None) -> None:
    body = await _search(client, "phồn vinh kỳ diệu")
    assert [i["term"] for i in body["items"]] == [WORD]


async def test_search_pagination(client: httpx.AsyncClient, dict_data: None) -> None:
    body = await _search(client, "xinmiao", size=1, page=2)
    assert len(body["items"]) == 1 and body["total"] == 3 and body["page"] == 2 and body["size"] == 1


async def test_search_without_results_returns_empty_page(client: httpx.AsyncClient, dict_data: None) -> None:
    body = await _search(client, "zqxjvk")
    assert body["items"] == [] and body["total"] == 0


async def test_search_rejects_empty_query(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/v1/dictionary/search", params={"q": ""})).status_code == 422
    blank = await client.get("/api/v1/dictionary/search", params={"q": "   "})
    assert blank.status_code == 400 and error_code(blank) == "EMPTY_QUERY"
    assert (await client.get("/api/v1/dictionary/search")).status_code == 422


async def test_search_does_not_treat_like_wildcards_as_patterns(
    client: httpx.AsyncClient, dict_data: None
) -> None:
    body = await _search(client, "%")
    assert body["total"] == 0


# ---------------------------------------------------------------- segment (F06.04, US-NH-29)


async def test_segment_splits_sentence_with_numbers_punctuation_and_latin(client: httpx.AsyncClient) -> None:
    res = await client.post("/api/v1/dictionary/segment", json={"text": "我吃了3个苹果, ok!"})
    assert res.status_code == 200, res.text
    tokens = res.json()["tokens"]
    assert "".join(t["text"] for t in tokens).replace(" ", "") == "我吃了3个苹果,ok!"
    for token in tokens:
        has_han = any("一" <= ch <= "鿿" for ch in token["text"])
        assert token["lookupable"] is has_han
        assert (token["pinyin"] is not None) is has_han
    non_lookupable = {t["text"] for t in tokens if not t["lookupable"]}
    assert {"3", ",", "ok", "!"} <= non_lookupable


async def test_segment_rejects_empty_text(client: httpx.AsyncClient) -> None:
    for text_value in ("", "   "):
        res = await client.post("/api/v1/dictionary/segment", json={"text": text_value})
        assert res.status_code == 400 and error_code(res) == "EMPTY_QUERY"


async def test_segment_rejects_too_long_text(client: httpx.AsyncClient) -> None:
    res = await client.post("/api/v1/dictionary/segment", json={"text": "我" * 1001})
    assert res.status_code == 422


# ---------------------------------------------------------------- characters (F06.05, US-NH-30)


async def test_characters_decompose_each_character(client: httpx.AsyncClient, dict_data: None) -> None:
    res = await client.get("/api/v1/dictionary/characters", params={"text": WORD})
    assert res.status_code == 200
    chars = res.json()["characters"]
    assert [c["ch"] for c in chars] == ["鑫", "淼"]
    assert chars[0]["radical"] == "金" and chars[0]["stroke_count"] == 24
    assert chars[1]["components"] == ["水"] and chars[1]["han_viet"] == "diểu"


async def test_characters_return_stroke_data_and_etymology(
    client: httpx.AsyncClient, dict_data: None
) -> None:
    """F06.05: trả nét viết để giao diện phát hoạt ảnh; chữ không có dữ liệu nét trả mảng rỗng."""
    res = await client.get("/api/v1/dictionary/characters", params={"text": "鑫淼"})
    first, second = res.json()["characters"]
    assert len(first["strokes"]) == len(first["medians"]) == 2
    assert first["medians"][0] == [[1, 2], [3, 4]]
    assert first["etymology"] == {"type": "pictophonetic", "hint": "gold", "phonetic": "金", "semantic": None}
    assert second["found"] is True and second["strokes"] == [] and second["medians"] == []
    assert second["etymology"] is None


async def test_characters_with_broken_stroke_data_still_found(
    client: httpx.AsyncClient, dict_data: None
) -> None:
    res = await client.get("/api/v1/dictionary/characters", params={"text": BROKEN_CHAR})
    char = res.json()["characters"][0]
    assert char["found"] is True and char["strokes"] == [] and char["medians"] == []
    assert char["radical"] == "土"


async def test_lookup_includes_stroke_data_for_logged_in_user(
    client: httpx.AsyncClient, dict_data: None
) -> None:
    account = await register(client)
    res = await client.get("/api/v1/dictionary/lookup", params={"term": WORD}, headers=account.headers)
    chars = res.json()["characters"]
    assert len(chars[0]["strokes"]) == 2 and chars[0]["etymology"]["hint"] == "gold"


async def test_characters_without_data_are_marked_not_found(
    client: httpx.AsyncClient, dict_data: None
) -> None:
    res = await client.get("/api/v1/dictionary/characters", params={"text": f"鑫{NO_DATA_CHAR}"})
    chars = res.json()["characters"]
    assert [(c["ch"], c["found"]) for c in chars] == [("鑫", True), (NO_DATA_CHAR, False)]


@pytest.mark.parametrize("text_value", ["鑫a", "鑫1", "abc", "鑫，"])
async def test_characters_reject_non_han(client: httpx.AsyncClient, text_value: str) -> None:
    res = await client.get("/api/v1/dictionary/characters", params={"text": text_value})
    assert res.status_code == 400 and error_code(res) == "INVALID_CHARACTER"


async def test_characters_records_decompose_event(
    app: FastAPI, client: httpx.AsyncClient, dict_data: None
) -> None:
    account = await register(client)
    await client.get("/api/v1/dictionary/characters", params={"text": WORD}, headers=account.headers)
    assert await _event_count(app, account.id, "decompose") == 1


# ---------------------------------------------------------------- word of the day


async def test_word_of_the_day_is_stable_within_a_day_and_uses_learner_level(
    client: httpx.AsyncClient, dict_data: None
) -> None:
    account = await register(client)
    await client.patch("/api/v1/settings", json={"hsk_level": 8}, headers=account.headers)
    first = await client.get("/api/v1/dictionary/word-of-the-day", headers=account.headers)
    second = await client.get("/api/v1/dictionary/word-of-the-day", headers=account.headers)
    assert first.status_code == 200, first.text
    assert first.json() == second.json()
    body = first.json()
    assert body["term"] == WOTD_WORD and body["hsk_level"] == 8 and body["meaning"] == "ba chữ vàng"


async def test_word_of_the_day_is_available_to_guests(client: httpx.AsyncClient, dict_data: None) -> None:
    res = await client.get("/api/v1/dictionary/word-of-the-day")
    assert res.status_code == 200 and res.json()["term"] == WOTD_WORD  # mặc định rơi về cấp có dữ liệu


async def test_word_of_the_day_returns_404_when_no_hsk_data(client: httpx.AsyncClient) -> None:
    res = await client.get("/api/v1/dictionary/word-of-the-day")
    if res.status_code == 200:  # CSDL kiểm thử đã được nạp dữ liệu thật: không kiểm tra nhánh rỗng
        pytest.skip("CSDL kiểm thử đã có dữ liệu HSK")
    assert res.status_code == 404 and error_code(res) == "NOT_FOUND"


# ---------------------------------------------------------------- admin import (F06.06, F06.07)

CVDICT_URL = "/api/v1/admin/dictionary/entries/import"
HSK_URL = "/api/v1/admin/dictionary/hsk/import"


def _cvdict_file(definition: str = "ba chữ vàng/ lấp lánh") -> dict[str, tuple[str, bytes, str]]:
    payload = {
        "鑫鑫鑫": {"trad": "鑫鑫鑫", "pinyin": "xin1 xin1 xin1", "definition": definition},
        "淼淼淼": {"trad": "淼淼淼", "pinyin": "miao3 miao3 miao3", "definition": "ba chấm nước"},
        "not han": {"pinyin": "abc", "definition": "bị bỏ qua"},
    }
    return {"file": ("cvdict.json", json.dumps(payload, ensure_ascii=False).encode(), "application/json")}


async def _admin(app: FastAPI, client: httpx.AsyncClient) -> Account:
    return await make_admin(app, client)


async def test_import_endpoints_require_admin(client: httpx.AsyncClient, dict_data: None) -> None:
    learner = await register(client)
    for url in (CVDICT_URL, HSK_URL):
        res = await client.post(url, files=_cvdict_file(), headers=learner.headers)
        assert res.status_code == 403 and error_code(res) == "PERMISSION_DENIED"
        assert (await client.post(url, files=_cvdict_file())).status_code == 401


async def test_admin_imports_dictionary_and_reimport_creates_no_duplicates(
    app: FastAPI, client: httpx.AsyncClient, dict_data: None
) -> None:
    """US-QT-09: báo cáo thêm/cập nhật/bỏ qua; nạp lại cùng tệp không sinh trùng."""
    admin = await _admin(app, client)
    first = await client.post(CVDICT_URL, files=_cvdict_file(), headers=admin.headers)
    assert first.status_code == 200, first.text
    assert (first.json()["added"], first.json()["updated"], first.json()["skipped"]) == (2, 0, 0)

    again = await client.post(CVDICT_URL, files=_cvdict_file(), headers=admin.headers)
    assert (again.json()["added"], again.json()["updated"], again.json()["skipped"]) == (0, 0, 2)

    changed = await client.post(CVDICT_URL, files=_cvdict_file("nghĩa mới"), headers=admin.headers)
    assert (changed.json()["added"], changed.json()["updated"], changed.json()["skipped"]) == (0, 1, 1)

    async with app.state.container.session_factory() as session:
        count = await session.scalar(
            text("SELECT count(*) FROM dict_entries WHERE source = 'cvdict' AND simplified = :w"),
            {"w": "鑫鑫鑫"},
        )
    assert count == 1
    found = await client.get("/api/v1/dictionary/lookup", params={"term": "鑫鑫鑫"})
    assert found.json()["found"] and found.json()["readings"][0]["definitions"][0]["gloss"] == "nghĩa mới"


async def test_admin_imports_hsk_csv_and_keeps_valid_rows(
    app: FastAPI, client: httpx.AsyncClient, dict_data: None
) -> None:
    """US-QT-10: dòng sai bị bỏ qua và báo lại, dòng đúng vẫn được nạp."""
    admin = await _admin(app, client)
    csv_text = "từ,cấp\n鑫鑫鑫,5\n淼淼淼,abc\n鑫鑫鑫鑫,12\n鑫鑫鑫鑫鑫,6\n"
    files = {"file": ("hsk.csv", csv_text.encode(), "text/csv")}
    res = await client.post(HSK_URL, files=files, headers=admin.headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["added"], body["updated"], body["skipped"]) == (2, 0, 0)
    assert body["rejected_count"] == 2 and len(body["rejected"]) == 2
    assert body["per_level"] == {"5": 1, "6": 1}

    again = await client.post(HSK_URL, files=files, headers=admin.headers)
    assert (again.json()["added"], again.json()["skipped"]) == (0, 2)
    listed = await client.get("/api/v1/dictionary/lookup", params={"term": "鑫鑫鑫"})
    assert listed.json()["hsk"] == {"level": 5, "source": "list"}


async def test_admin_imports_hsk_json_with_new_labels(
    app: FastAPI, client: httpx.AsyncClient, dict_data: None
) -> None:
    admin = await _admin(app, client)
    payload = [
        {"simplified": "鑫鑫鑫", "level": ["new-3", "old-1"], "pos": ["n"], "forms": []},
        {"simplified": "鑫鑫鑫", "level": ["new-6"], "pos": ["v"], "forms": []},
        {"simplified": "淼淼淼", "level": ["old-2"], "pos": [], "forms": []},
    ]
    files = {"file": ("hsk.json", json.dumps(payload, ensure_ascii=False).encode(), "application/json")}
    res = await client.post(HSK_URL, files=files, headers=admin.headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["added"] == 1 and body["rejected_count"] == 1 and body["per_level"] == {"3": 1}


@pytest.mark.parametrize("url", [CVDICT_URL, HSK_URL])
async def test_admin_import_rejects_broken_file(app: FastAPI, client: httpx.AsyncClient, url: str) -> None:
    admin = await _admin(app, client)
    files = {"file": ("broken.json", b"\xff\xfe\x00 not a dictionary", "application/json")}
    res = await client.post(url, files=files, headers=admin.headers)
    assert res.status_code == 400 and error_code(res) == "DICTIONARY_FILE_INVALID"
    broken_json = {"file": ("broken.json", b"{ unfinished", "application/json")}
    if url == CVDICT_URL:
        res = await client.post(url, files=broken_json, headers=admin.headers)
        assert res.status_code == 400 and error_code(res) == "DICTIONARY_FILE_INVALID"


async def test_admin_import_requires_file(app: FastAPI, client: httpx.AsyncClient) -> None:
    admin = await _admin(app, client)
    res = await client.post(CVDICT_URL, headers=admin.headers)
    assert res.status_code == 422


async def test_find_entry_ids_returns_smallest_id_per_simplified_word(app: FastAPI, dict_data: None) -> None:
    factory: Factory = app.state.container.session_factory
    async with factory() as session:
        smallest = (
            await session.execute(
                select(func.min(DictEntryModel.id)).where(DictEntryModel.simplified == WORD)
            )
        ).scalar_one()
    async with SqlDictionaryUnitOfWork(factory) as uow:
        found = await uow.reader.find_entry_ids([WORD, WORD, WOTD_WORD, LISTED])

    assert found[WORD] == smallest
    assert WOTD_WORD in found and LISTED not in found
