"""M16 - Mini-game "Gõ pinyin chém chữ" qua API thật (F16.01, US-NH-81).

CSDL kiểm thử thiếu `hanzi`/`hsk_words` nên mỗi test tự chèn chữ hiếm (khối CJK mở rộng A) rồi dọn lại.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text

from tests.helpers import Account, error_code, register

pytestmark = pytest.mark.integration

G = "/api/v1/gamification"
VOCAB = "/api/v1/vocab-entries"
ROUNDS = f"{G}/minigames/blade/rounds"
SESSIONS = f"{G}/minigames/blade/sessions"
BEST = f"{G}/minigames/blade/best"
BAND6_CHARS = [chr(0x3500 + i) for i in range(30)]
BAND3_CHARS = [chr(0x3540 + i) for i in range(26)]
RADICAL = "㐄"
SAVED_CHARS = BAND6_CHARS[:22]  # có bộ thủ RADICAL, người chơi lưu vào Sổ tay ở test bộ thủ yếu
READINGS = ("mā", "nǚ", "le liǎo")
EXPECTED_ANSWERS = (["ma"], ["nu"], ["le", "liao"])
FIRST_WORD_READING = "lǜ sè"
STEP_MS = 200  # đủ chậm với mọi đáp án (boss "nihao" cần ≥ 175 ms)
HIT_POINTS, BOSS_FACTOR, LIFE_BONUS, LIVES = 10, 3, 5, 3


def _pairs(chars: list[str]) -> list[str]:
    return [chars[i] + chars[i + 1] for i in range(0, len(chars), 2)]


BAND6_WORDS, BAND3_WORDS = _pairs(BAND6_CHARS), _pairs(BAND3_CHARS)


async def _exec(app: FastAPI, sql: str, **params: object) -> None:
    async with app.state.container.session_factory() as session:
        await session.execute(text(sql), params)
        await session.commit()


async def _scalar(app: FastAPI, sql: str, **params: object) -> object:
    async with app.state.container.session_factory() as session:
        return (await session.execute(text(sql), params)).scalar_one()


@pytest.fixture
async def seeded(app: FastAPI, client: httpx.AsyncClient) -> AsyncIterator[None]:
    """Chèn chữ và từ HSK riêng: cấp 6 (30 chữ, 15 từ) và cấp 3 (26 chữ, 13 từ)."""
    for index, ch in enumerate(BAND6_CHARS + BAND3_CHARS):
        radical = RADICAL if ch in SAVED_CHARS else None
        await _exec(
            app,
            "INSERT INTO hanzi (ch, pinyin, han_viet, radical, components) VALUES "
            "(:ch, :p, :hv, CAST(:r AS text), CASE WHEN CAST(:r AS text) IS NULL THEN NULL "
            "ELSE ARRAY[CAST(:r AS text)] END) ON CONFLICT (ch) DO UPDATE SET pinyin = EXCLUDED.pinyin, "
            "han_viet = EXCLUDED.han_viet, radical = EXCLUDED.radical, components = EXCLUDED.components",
            ch=ch,
            p=READINGS[index % 3],
            hv=f"hv{index}",
            r=radical,
        )
    for level, words in ((6, BAND6_WORDS), (3, BAND3_WORDS)):
        for word in words:
            reading = FIRST_WORD_READING if word == BAND6_WORDS[0] else "nǐ hǎo"
            await _exec(
                app,
                "INSERT INTO hsk_words (word, level, pinyin) VALUES (:w, :l, :p) "
                "ON CONFLICT (word) DO UPDATE SET level = EXCLUDED.level, pinyin = EXCLUDED.pinyin",
                w=word,
                l=level,
                p=reading,
            )
    try:
        yield
    finally:
        await _exec(app, "DELETE FROM hsk_words WHERE word = ANY(:w)", w=BAND6_WORDS + BAND3_WORDS)
        await _exec(app, "DELETE FROM hanzi WHERE ch = ANY(:c)", c=BAND6_CHARS + BAND3_CHARS)


async def _new_round(client: httpx.AsyncClient, who: Account, **body: Any) -> dict[str, Any]:
    res = await client.post(ROUNDS, json={"mode": "hsk", "hsk_band": 6, **body}, headers=who.headers)
    assert res.status_code == 200, res.text
    data: dict[str, Any] = res.json()
    return data


async def _backdate(app: FastAPI, rnd: dict[str, Any], seconds: int = 60) -> None:
    """Lùi giờ phát lượt để đồng hồ máy chủ đã chạy đủ lâu cho chuỗi sự kiện của test."""
    await _exec(
        app,
        "UPDATE minigame_rounds SET issued_at = now() - make_interval(secs => :s) "
        "WHERE id = CAST(:r AS uuid)",
        s=seconds,
        r=rnd["round_id"],
    )


def _hits(count: int) -> list[dict[str, Any]]:
    return [{"index": i, "result": "hit", "ms": (i + 1) * STEP_MS} for i in range(count)]


def _body(rnd: dict[str, Any], events: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {"round_id": rnd["round_id"], "events": events, "typos": 0, "duration_ms": 30_000, **extra}


def _perfect_score(rnd: dict[str, Any]) -> int:
    """Điểm kỳ vọng khi chém đúng cả bộ mục theo thứ tự (viết lại công thức độc lập với mã nguồn)."""
    score = 0
    for combo, item in enumerate(rnd["items"], start=1):
        base = HIT_POINTS * (BOSS_FACTOR if item["is_boss"] else 1)
        score += base * min(6, 2 + combo // 5) // 2
    return score + LIFE_BONUS * LIVES


async def test_blade_round_has_100_items_with_answers_filtered_by_band(
    app: FastAPI, client: httpx.AsyncClient, seeded: None
) -> None:
    """US-NH-81: 100 mục, 1/10 boss, đáp án a-z (ü, đa âm, boss), chữ/từ đúng cấp HSK; lượt được lưu."""
    who = await register(client)
    rnd = await _new_round(client, who)
    items = rnd["items"]
    assert (rnd["mode"], rnd["hsk_band"], rnd["radical"], rnd["seconds"], rnd["lives"]) == (
        "hsk",
        6,
        None,
        120,
        3,
    )
    assert [i["index"] for i in items] == list(range(100))
    bosses = [i for i in items if i["is_boss"]]
    assert len(bosses) == 10 and all(b["text"] in BAND6_WORDS for b in bosses)
    assert all(b["answers"] == (["luse"] if b["text"] == BAND6_WORDS[0] else ["nihao"]) for b in bosses)
    singles = {i["text"]: i for i in items if not i["is_boss"]}
    assert set(BAND6_CHARS) <= set(singles)  # chữ mới của cấp 6 luôn có mặt
    for index, ch in enumerate(BAND6_CHARS):
        assert singles[ch]["answers"] == EXPECTED_ANSWERS[index % 3], ch
        assert singles[ch]["pinyin"] == READINGS[index % 3] and singles[ch]["hsk_level"] == 6
        assert singles[ch]["han_viet"] == f"hv{index}"
    stored = await _scalar(
        app,
        "SELECT jsonb_array_length(items) FROM minigame_rounds WHERE id = CAST(:r AS uuid) AND user_id = :u "
        "AND mode = 'hsk' AND hsk_band = 6 AND radical IS NULL",
        r=rnd["round_id"],
        u=who.id,
    )
    assert stored == 100

    lower = await _new_round(client, who, hsk_band=3)
    texts = {i["text"] for i in lower["items"]}
    assert texts.isdisjoint(BAND6_CHARS) and set(BAND3_CHARS) <= texts
    assert all(i["text"] in BAND3_WORDS for i in lower["items"] if i["is_boss"])


async def test_blade_round_rejects_bad_requests_and_old_endpoints_are_gone(
    client: httpx.AsyncClient, seeded: None
) -> None:
    who = await register(client)

    async def post(body: dict[str, Any]) -> httpx.Response:
        return await client.post(ROUNDS, json=body, headers=who.headers)

    missing_band = await post({"mode": "hsk"})
    assert (missing_band.status_code, error_code(missing_band)) == (400, "INVALID_MINIGAME_REQUEST")
    missing_radical = await post({"mode": "weak_radical"})
    assert (missing_radical.status_code, error_code(missing_radical)) == (400, "INVALID_MINIGAME_REQUEST")
    for bad in ({"mode": "hsk", "hsk_band": 8}, {"mode": "hsk", "hsk_band": 0}, {"mode": "khac"}):
        assert (await post(bad)).status_code == 422, bad
    nothing = await post({"mode": "weak_radical", "radical": "龘"})
    assert (nothing.status_code, error_code(nothing)) == (409, "NOT_ENOUGH_WORDS_FOR_GAME")

    for old in ("rounds", "sessions"):
        res = await client.post(
            f"{G}/minigames/radicals/{old}", json={"radical": RADICAL}, headers=who.headers
        )
        assert res.status_code in (404, 405), old
    assert (await client.get(f"{G}/minigames/radicals/weak", headers=who.headers)).status_code == 200


async def test_blade_weak_radical_mode_uses_saved_chars_with_that_radical(
    app: FastAPI, client: httpx.AsyncClient, seeded: None
) -> None:
    """Chế độ bộ thủ yếu: chữ có bộ thủ đó từ Sổ tay; ván không có cấp HSK; kỷ lục tách riêng."""
    who = await register(client)
    for ch in SAVED_CHARS:
        saved = await client.post(VOCAB, json={"term": ch, "source": "manual"}, headers=who.headers)
        assert saved.status_code == 201, saved.text
    res = await client.post(ROUNDS, json={"mode": "weak_radical", "radical": RADICAL}, headers=who.headers)
    assert res.status_code == 200, res.text
    rnd = res.json()
    assert (rnd["mode"], rnd["hsk_band"], rnd["radical"]) == ("weak_radical", None, RADICAL)
    assert len(rnd["items"]) == 100 and {i["text"] for i in rnd["items"]} == set(SAVED_CHARS)
    await _backdate(app, rnd)
    done = await client.post(SESSIONS, json=_body(rnd, _hits(100)), headers=who.headers)
    assert done.status_code == 201, done.text
    assert (done.json()["mode"], done.json()["hsk_band"], done.json()["radical"]) == (
        "weak_radical",
        None,
        RADICAL,
    )
    best = (await client.get(BEST, headers=who.headers)).json()
    assert [(b["mode"], b["hsk_band"], b["plays"]) for b in best] == [("weak_radical", None, 1)]


async def test_blade_scores_are_computed_by_the_server_and_xp_best_and_missed_are_returned(
    app: FastAPI, client: httpx.AsyncClient, seeded: None
) -> None:
    """US-NH-81: máy chủ chấm lại (bỏ qua score gửi lên); XP = min(10, hit // 2), 5 ván/ngày; kỷ lục."""
    who = await register(client)
    first_round = await _new_round(client, who)
    await _backdate(app, first_round)
    first = await client.post(
        SESSIONS, json=_body(first_round, _hits(100), score=999_999), headers=who.headers
    )
    assert first.status_code == 201, first.text
    data = first.json()
    assert data["score"] == _perfect_score(first_round) and data["score"] != 999_999
    assert (data["correct"], data["wrong"], data["typos"], data["max_combo"]) == (100, 0, 0, 100)
    assert (data["accuracy"], data["rank"], data["xp_awarded"], data["is_best"]) == (1.0, "S", 10, True)
    assert (data["mode"], data["hsk_band"], data["radical"], data["missed"]) == ("hsk", 6, None, [])
    assert data["duration_ms"] == 30_000  # số trình duyệt báo, không vượt số đo máy chủ (~60 giây)

    reused = await client.post(SESSIONS, json=_body(first_round, _hits(100)), headers=who.headers)
    assert (reused.status_code, error_code(reused)) == (409, "MINIGAME_ROUND_USED")

    second_round = await _new_round(client, who)
    await _backdate(app, second_round)
    dropped = second_round["items"][1]
    events = [
        {"index": 0, "result": "hit", "ms": 200},
        {"index": 1, "result": "miss", "ms": 400},
        {"index": 2, "result": "hit", "ms": 600},
    ]
    second = await client.post(SESSIONS, json=_body(second_round, events, typos=2), headers=who.headers)
    assert second.status_code == 201, second.text
    low = second.json()
    assert (low["correct"], low["wrong"], low["typos"], low["max_combo"]) == (2, 1, 2, 1)
    assert low["missed"] == [
        {"text": dropped["text"], "pinyin": dropped["pinyin"], "han_viet": dropped["han_viet"]}
    ]
    assert (low["xp_awarded"], low["is_best"], 0 < low["accuracy"] < 1) == (1, False, True)

    awarded = [data["xp_awarded"], low["xp_awarded"]]
    best_so_far = data["score"]
    for _ in range(4):
        rnd = await _new_round(client, who)
        await _backdate(app, rnd)
        res = await client.post(SESSIONS, json=_body(rnd, _hits(100)), headers=who.headers)
        assert res.status_code == 201, res.text
        awarded.append(res.json()["xp_awarded"])
        # Vị trí boss khác nhau nên điểm mỗi lượt khác nhau; chỉ ván vượt kỷ lục cũ mới có is_best.
        assert res.json()["is_best"] is (res.json()["score"] > best_so_far)
        best_so_far = max(best_so_far, res.json()["score"])
    assert awarded == [10, 1, 10, 10, 10, 0]  # chỉ 5 ván đầu tiên mỗi ngày được tính XP
    me = (await client.get(f"{G}/me", headers=who.headers)).json()
    assert me["xp_today"] == 41

    best = (await client.get(BEST, headers=who.headers)).json()
    assert best == [{"mode": "hsk", "hsk_band": 6, "best_score": best_so_far, "best_combo": 100, "plays": 6}]
    stranger = await register(client)
    assert (await client.get(BEST, headers=stranger.headers)).json() == []
    game_type = await _scalar(app, "SELECT game_type FROM minigame_sessions WHERE id = :i", i=low["id"])
    assert game_type == "pinyin_blade"


@pytest.mark.parametrize(
    "events",
    [
        [{"index": 100, "result": "hit", "ms": 400}],  # chỉ số không có trong lượt
        [{"index": 0, "result": "hit", "ms": 300}, {"index": 0, "result": "hit", "ms": 900}],  # lặp mục
        [{"index": 0, "result": "hit", "ms": 900}, {"index": 1, "result": "hit", "ms": 400}],  # ms giảm
        [{"index": 0, "result": "hit", "ms": 5}],  # bot: quá nhanh
        [{"index": 0, "result": "hit", "ms": 900_000}],  # vượt thời gian máy chủ
        [{"index": i, "result": "miss", "ms": 100 * (i + 1)} for i in range(4)],  # chơi tiếp sau khi hết mạng
    ],
)
async def test_blade_rejects_forged_events_without_burning_the_round(
    app: FastAPI, client: httpx.AsyncClient, seeded: None, events: list[dict[str, Any]]
) -> None:
    who = await register(client)
    rnd = await _new_round(client, who)
    await _backdate(app, rnd)
    res = await client.post(SESSIONS, json=_body(rnd, events), headers=who.headers)
    assert (res.status_code, error_code(res)) == (400, "INVALID_MINIGAME_RESULT"), res.text
    ok = await client.post(SESSIONS, json=_body(rnd, _hits(3)), headers=who.headers)  # lượt chưa bị đốt
    assert ok.status_code == 201, ok.text


async def test_blade_rejects_bad_durations_and_malformed_bodies(
    app: FastAPI, client: httpx.AsyncClient, seeded: None
) -> None:
    who = await register(client)
    rnd = await _new_round(client, who)
    await _backdate(app, rnd)
    for duration in (500, 130_000):
        res = await client.post(
            SESSIONS, json=_body(rnd, _hits(3), duration_ms=duration), headers=who.headers
        )
        assert (res.status_code, error_code(res)) == (400, "INVALID_MINIGAME_RESULT"), duration
    too_many = _hits(1) * 301
    for bad in (
        _body(rnd, too_many),
        _body(rnd, _hits(3), typos=-1),
        _body(rnd, [{"index": 0, "result": "oops", "ms": 300}]),
        {"round_id": "không-phải-uuid", "events": [], "typos": 0, "duration_ms": 5_000},
        {"radical": RADICAL, "shown": ["a"], "selected": ["a"], "duration_ms": 20_000},  # hợp đồng cũ
    ):
        assert (await client.post(SESSIONS, json=bad, headers=who.headers)).status_code == 422


async def test_blade_round_cannot_be_stolen_forged_expired_or_submitted_concurrently(
    app: FastAPI, client: httpx.AsyncClient, seeded: None
) -> None:
    """US-NH-81: lượt giả/của người khác → 404; quá hạn → 409; ba yêu cầu đồng thời chỉ một lần được nhận."""
    who, thief = await register(client), await register(client)
    forged = await client.post(
        SESSIONS,
        json={
            "round_id": "00000000-0000-4000-8000-000000000000",
            "events": [],
            "typos": 0,
            "duration_ms": 5_000,
        },
        headers=who.headers,
    )
    assert (forged.status_code, error_code(forged)) == (404, "MINIGAME_ROUND_NOT_FOUND")

    stolen_round = await _new_round(client, who)
    stolen = await client.post(SESSIONS, json=_body(stolen_round, _hits(3)), headers=thief.headers)
    assert (stolen.status_code, error_code(stolen)) == (404, "MINIGAME_ROUND_NOT_FOUND")
    assert (
        await client.post(SESSIONS, json=_body(stolen_round, _hits(3)), headers=who.headers)
    ).status_code == 201

    expired_round = await _new_round(client, who)
    await _backdate(app, expired_round, seconds=600)
    late = await client.post(SESSIONS, json=_body(expired_round, _hits(3)), headers=who.headers)
    assert (late.status_code, error_code(late)) == (409, "MINIGAME_ROUND_EXPIRED")

    racing_round = await _new_round(client, who)
    await _backdate(app, racing_round)
    results = await asyncio.gather(
        *(client.post(SESSIONS, json=_body(racing_round, _hits(10)), headers=who.headers) for _ in range(3))
    )
    assert sorted(r.status_code for r in results) == [201, 409, 409], [r.text for r in results]
    sessions = await _scalar(app, "SELECT count(*) FROM minigame_sessions WHERE user_id = :u", u=who.id)
    assert sessions == 2  # lượt đầu và lượt thắng cuộc đua; lượt giả, bị đánh cắp, quá hạn không có ván
