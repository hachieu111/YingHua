"""M16 Gamification - XP, nhiệm vụ, mục tiêu tuần, bảng xếp hạng, mùa, huy hiệu, mini-game (F16.01–F16.12).

Chạy trên CSDL kiểm thử với API thật. Các test không giả định CSDL trống (nó tích lũy người dùng và XP qua các
chạy) nên so sánh hạng tương đối và số liệu của chính tài khoản vừa tạo.
"""

from __future__ import annotations

import random
import uuid
from datetime import date, datetime, time, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text

from app.modules.auth.application.public import Identity, Role
from app.modules.gamification.application.public import FinalizeSeasonsUseCase
from app.modules.gamification.domain.season_rules import VN_TZ
from app.modules.gamification.infrastructure.public import SqlGamificationUnitOfWork
from tests.api.test_imaging_reader import _new_page
from tests.helpers import Account, error_code, make_admin, register

pytestmark = pytest.mark.integration

API = "/api/v1"
G = f"{API}/gamification"
VOCAB = f"{API}/vocab-entries"
BLOCK = "㐀㐁㐂㐃㐅㐆㐇㐈"  # chữ Hán mở rộng A hiếm, không trùng dữ liệu từ điển thật


async def _exec(app: FastAPI, sql: str, **params: object) -> None:
    async with app.state.container.session_factory() as session:
        await session.execute(text(sql), params)
        await session.commit()


async def _scalar(app: FastAPI, sql: str, **params: object) -> object:
    async with app.state.container.session_factory() as session:
        return (await session.execute(text(sql), params)).scalar_one()


def _parse(value: str) -> datetime:
    """ISO 8601 UTC dạng "…Z" (Python 3.10 chưa đọc được hậu tố Z)."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def _save(client: httpx.AsyncClient, who: Account, term: str) -> httpx.Response:
    return await client.post(VOCAB, json={"term": term, "source": "manual"}, headers=who.headers)


async def _get(client: httpx.AsyncClient, who: Account, path: str) -> dict:  # type: ignore[type-arg]
    res = await client.get(f"{G}{path}", headers=who.headers)
    assert res.status_code == 200, res.text
    return res.json()  # type: ignore[no-any-return]


async def test_every_endpoint_needs_login_and_there_is_no_endpoint_to_send_xp(
    client: httpx.AsyncClient,
) -> None:
    """US-NH-84: khách bị 401; trình duyệt không có API nào để tự cộng XP."""
    for path in ("/me", "/me/weekly-activity", "/quests/today", "/weekly-goal", "/leaderboard"):
        assert (await client.get(f"{G}{path}")).status_code == 401, path
    for path in ("/seasons/current", "/seasons/me", "/achievements", "/minigames/radicals/weak"):
        assert (await client.get(f"{G}{path}")).status_code == 401, path
    assert (await client.get(f"{G}/minigames/blade/best")).status_code == 401
    for path in ("/minigames/blade/rounds", "/minigames/blade/sessions"):
        assert (await client.post(f"{G}{path}", json={})).status_code == 401, path
    assert (await client.put(f"{G}/achievements/equipped", json={})).status_code == 401
    account = await register(client)
    for method in ("POST", "PUT", "PATCH"):
        res = await client.request(method, f"{G}/xp", json={"amount": 999}, headers=account.headers)
        assert res.status_code in (404, 405), (method, res.status_code)
    assert (await _get(client, account, "/me"))["xp_total"] == 0


async def test_new_user_sees_zeroes_and_default_goal(client: httpx.AsyncClient) -> None:
    """US-NH-84/85/86 (người dùng mới): mọi số bằng 0, 3 nhiệm vụ, mục tiêu tuần mặc định 20, 7 ô rỗng."""
    who = await register(client)
    me = await _get(client, who, "/me")
    assert (me["xp_today"], me["xp_season"], me["xp_total"], me["season_rank"]) == (0, 0, 0, None)
    assert me["streak_current"] == 0 and me["equipped_badge"] is None
    assert me["next_streak_milestone"] == {"days": 7, "days_left": 7}

    week = await _get(client, who, "/me/weekly-activity")
    assert len(week["days"]) == 7 and week["total"] == 0
    first = date.fromisoformat(week["week_start"])
    assert first.weekday() == 0 and week["days"][0]["date"] == week["week_start"]

    quests = await _get(client, who, "/quests/today")
    assert [q["code"] for q in quests["quests"]] == ["read_pages", "review_cards", "take_quiz"]
    assert [(q["target"], q["xp"]) for q in quests["quests"]] == [(2, 20), (15, 15), (1, 30)]
    assert quests["completed_count"] == 0 and quests["total"] == 3 and quests["bonus_coins"] == 20

    goal = await _get(client, who, "/weekly-goal")
    assert (goal["goal"], goal["pages_read"], goal["pages_left"], goal["percent"]) == (20, 0, 20, 0)
    assert (goal["reward_xp"], goal["reward_frame_code"], goal["reward_frame_days"]) == (
        150,
        "sakura_gold",
        7,
    )
    assert goal["rewarded_at"] is None

    patched = await client.patch(f"{API}/settings", json={"weekly_page_goal": 5}, headers=who.headers)
    assert patched.status_code == 200
    low = await _get(client, who, "/weekly-goal")
    assert (low["goal"], low["rewarded_goal"]) == (5, 10)  # hiển thị đúng số đã đặt, thưởng cần từ 10 trang


async def test_words_reviews_and_pages_award_xp_once_and_complete_quests(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-84 TC1–TC5, US-NH-85: XP do máy chủ ghi, chống cộng trùng, nhiệm vụ thưởng tự động."""
    who = await register(client)
    saved = await _save(client, who, "学习")
    assert saved.status_code == 201, saved.text
    entry_id = saved.json()["entry"]["id"]
    assert (await _get(client, who, "/me"))["xp_today"] == 3

    # Lưu lại từ đã có, hoặc xóa rồi lưu lại, đều không cộng thêm.
    await _save(client, who, "学习")
    assert (await client.delete(f"{VOCAB}/{entry_id}", headers=who.headers)).status_code == 204
    assert (await _save(client, who, "学习")).status_code == 201
    me = await _get(client, who, "/me")
    assert (me["xp_today"], me["xp_total"], me["xp_season"]) == (3, 3, 3) and me["season_rank"] is not None

    # Chấm thẻ +1 XP; bấm đúp cùng presentation_id không tính lần hai.
    due = (await client.get(f"{API}/cards/due?size=100", headers=who.headers)).json()["items"]
    presentation = str(uuid.uuid4())
    for _ in range(2):
        res = await client.post(
            f"{API}/cards/{due[0]['id']}/grade",
            json={"rating": 3, "presentation_id": presentation},
            headers=who.headers,
        )
        assert res.status_code == 200, res.text
    assert (await _get(client, who, "/me"))["xp_today"] == 4

    # Đọc 2 trang mới: +2 XP mỗi trang, rồi nhiệm vụ "Đọc 2 trang" +20 XP tự động.
    page_one = await _new_page(client, who)
    page_two = await _new_page(client, who, page_one["series_id"], page_one["chapter_id"])
    chapter = page_one["chapter_id"]
    for number in (page_one["page_no"], page_two["page_no"], page_two["page_no"]):
        res = await client.put(
            f"{API}/chapters/{chapter}/progress", json={"page_no": number}, headers=who.headers
        )
        assert res.status_code == 200, res.text
    me = await _get(client, who, "/me")
    assert me["xp_today"] == 4 + 2 + 2 + 20 and me["streak_current"] == 1
    quests = await _get(client, who, "/quests/today")
    read = quests["quests"][0]
    assert read["completed"] and read["progress"] == 2 and read["rewarded_at"] is not None
    assert quests["completed_count"] == 1 and quests["bonus_granted"] is False
    week = await _get(client, who, "/me/weekly-activity")
    assert week["total"] == me["xp_total"]

    goal = await _get(client, who, "/weekly-goal")
    assert goal["pages_read"] == 2 and goal["pages_left"] == 18 and goal["percent"] == 10

    # Sổ XP chỉ thêm, có khóa chống trùng: không có dòng nào cho cùng (người, nguồn, mã).
    dup = await _scalar(
        app,
        "SELECT count(*) FROM (SELECT 1 FROM xp_events WHERE user_id = :u "
        "GROUP BY source, source_ref HAVING count(*) > 1) t",
        u=who.id,
    )
    assert dup == 0


async def test_weekly_goal_and_quest_bonus_reach_the_real_wallet_exactly_once(
    client: httpx.AsyncClient,
) -> None:
    """US-NH-86: đạt mục tiêu tuần +150 XP, khung Hoa Anh Đào Vàng 7 ngày; US-NH-85: xu chỉ khi đủ 3/3."""
    who = await register(client)
    assert (
        await client.patch(f"{API}/settings", json={"weekly_page_goal": 10}, headers=who.headers)
    ).status_code == 200
    coins_before = (await client.get(f"{API}/rewards/wallet", headers=who.headers)).json()["coin_balance"]

    first = await _new_page(client, who)
    pages = [first] + [
        await _new_page(client, who, first["series_id"], first["chapter_id"]) for _ in range(9)
    ]
    for page in pages:
        url = f"{API}/chapters/{first['chapter_id']}/progress"
        assert (
            await client.put(url, json={"page_no": page["page_no"]}, headers=who.headers)
        ).status_code == 200

    goal = await _get(client, who, "/weekly-goal")
    assert goal["pages_read"] == 10 and goal["percent"] == 100 and goal["rewarded_at"] is not None
    me = await _get(client, who, "/me")
    assert me["xp_today"] == 10 * 2 + 20 + 150  # 10 trang + nhiệm vụ đọc trang + mục tiêu tuần
    frames = {f["code"]: f for f in (await client.get(f"{API}/rewards/frames", headers=who.headers)).json()}
    gold = frames["sakura_gold"]
    assert gold["owned"] is True and gold["expires_at"] is not None
    left = _parse(gold["expires_at"]) - datetime.now(timezone.utc)
    assert timedelta(days=6, hours=23) < left <= timedelta(days=7)

    # Thêm 15 lượt lật thẻ (15 từ khác nhau, mỗi từ một thẻ mỗi ngày): mới 2/3 nhiệm vụ nên chưa có xu thưởng.
    terms = list("的一是不了人我在有他这中大来上国个到说们")[:15]
    for term in terms:
        assert (await _save(client, who, term)).status_code == 201
    due = (await client.get(f"{API}/cards/due?size=100", headers=who.headers)).json()["items"]
    seen: set[int] = set()
    for card in due:
        if card["vocab_entry_id"] in seen or len(seen) == 15:
            continue
        seen.add(card["vocab_entry_id"])
        res = await client.post(
            f"{API}/cards/{card['id']}/grade",
            json={"rating": 3, "presentation_id": str(uuid.uuid4())},
            headers=who.headers,
        )
        assert res.status_code == 200, res.text
    quests = await _get(client, who, "/quests/today")
    assert [q["completed"] for q in quests["quests"]] == [True, True, False]
    coins = (await client.get(f"{API}/rewards/wallet", headers=who.headers)).json()["coin_balance"]
    assert coins == coins_before  # chưa làm bài kiểm tra nên chưa có xu thưởng nhiệm vụ

    ledger = (await client.get(f"{API}/rewards/wallet/ledger?currency=coin", headers=who.headers)).json()
    assert all(item["reason"] != "quest_bonus" for item in ledger["items"])


async def test_leaderboard_ranks_by_xp_hides_email_and_hidden_users_and_excludes_locked(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-88, US-NH-89: xếp hạng theo XP, admin được xếp hạng, tài khoản khóa bị loại, ẩn danh giữ hạng."""
    suffix = uuid.uuid4().hex[:6]
    top = await register(client, display_name=f"Top {suffix}")
    middle = await register(client, display_name=f"Giua {suffix}")
    low = await register(client, display_name=f"Thap {suffix}")
    locked = await register(client, display_name=f"Khoa {suffix}")
    admin = await make_admin(app, client)
    for who, terms in (
        (top, "我你他她"),
        (middle, "我你他"),
        (low, "我你"),
        (admin, "我你"),
        (locked, "我你他她它"),
    ):
        for term in terms:
            assert (await _save(client, who, term)).status_code == 201

    board = await _get(client, top, "/leaderboard?metric=exp&period=week&size=100")
    assert board["me"]["score"] == 12 and board["me"]["is_me"] and board["me"]["unit"] == "XP"
    ranks = {}
    for name, who in (("top", top), ("middle", middle), ("low", low), ("admin", admin), ("locked", locked)):
        mine = (await _get(client, who, "/leaderboard"))["me"]
        ranks[name] = mine["rank"]
    assert None not in ranks.values()
    assert ranks["locked"] < ranks["top"] < ranks["middle"] < ranks["low"]  # 15 > 12 > 9 > 6 XP
    assert ranks["admin"] is not None  # quản trị viên được xếp hạng như người học (30/10/2026)

    total_before = board["total"]
    lock = await client.post(
        f"{API}/admin/users/{locked.id}/lock", json={"reason": "Kiểm thử"}, headers=admin.headers
    )
    assert lock.status_code == 200, lock.text
    after_lock = await _get(client, top, "/leaderboard?size=100")
    assert after_lock["total"] == total_before - 1  # tài khoản bị khóa không còn trong bảng
    assert after_lock["summary"]["learners"] >= 4 and after_lock["summary"]["season_xp"] >= 12 + 9 + 6 + 6
    assert "@" not in str(after_lock) and "email" not in str(after_lock).lower()
    assert all("user_id" not in row for row in after_lock["items"])

    # Ẩn danh: người khác thấy "Học viên ẩn danh" đúng hạng và điểm; chính mình vẫn thấy đủ.
    rank_before = (await _get(client, middle, "/leaderboard"))["me"][
        "rank"
    ]  # đổi sau khi tài khoản khóa rời bảng
    assert rank_before == ranks["middle"] - 1
    hide = await client.patch(f"{API}/settings", json={"show_on_leaderboard": False}, headers=middle.headers)
    assert hide.status_code == 200 and hide.json()["show_on_leaderboard"] is False
    page = (rank_before - 1) // 20 + 1
    seen = await _get(client, top, f"/leaderboard?metric=exp&period=week&size=20&page={page}")
    row = next(r for r in seen["items"] if r["rank"] == rank_before)
    assert row["anonymous"] and row["display_name"] == "Học viên ẩn danh" and row["score"] == 9
    assert row["avatar_url"] is None and row["hsk_level"] is None and row["badge"] is None
    assert row["frame"] is None and row["is_vip"] is False
    own = await _get(client, middle, "/leaderboard")
    assert own["me"]["display_name"] == f"Giua {suffix}" and own["me"]["rank"] == rank_before
    assert own["me_hidden"] is True and own["me_hidden_note"] == "Bạn đang ẩn tên trên bảng xếp hạng"
    assert not own["me"]["anonymous"]

    # Chỉ số khác và tham số sai.
    vocab = await _get(client, top, "/leaderboard?metric=vocab&period=all")
    assert vocab["me"]["score"] == 4 and vocab["me"]["unit"] == "từ"
    pages = await _get(client, top, "/leaderboard?metric=pages&period=month")
    assert pages["me"]["rank"] is None and pages["me"]["score"] == 0  # chưa đọc trang nào: dòng "Bạn" 0 điểm
    assert (await _get(client, top, "/leaderboard?metric=streak&period=all"))["me"]["unit"] == "ngày"
    for query in ("size=101", "metric=foo", "period=year", "page=0"):
        assert (await client.get(f"{G}/leaderboard?{query}", headers=top.headers)).status_code == 422, query
    milestone = (await _get(client, low, "/leaderboard"))["next_milestone"]
    assert milestone is None or (milestone["rank"] in (50, 10, 3, 1) and milestone["xp_missing"] >= 0)


async def test_equip_badge_flow_keeps_at_most_one_equipped(app: FastAPI, client: httpx.AsyncClient) -> None:
    """US-NH-91, US-NH-92: danh sách huy hiệu kèm tiến độ; chỉ đeo được huy hiệu đã mở khóa, tối đa một."""
    who = await register(client)
    await _save(client, who, "我")
    listing = (await client.get(f"{G}/achievements", headers=who.headers)).json()
    assert [a["code"] for a in listing] == [
        "sakura_member", "top_scholar", "manhua_elite", "seed_sower", "hsk3_master", "night_owl",
        "apprentice_translator",
    ]  # fmt: skip
    seed = next(a for a in listing if a["code"] == "seed_sower")
    assert (seed["tier"], seed["progress"], seed["next_threshold"], seed["max_tier"]) == (0, 1, 300, 3)
    assert all(not a["equipped"] and a["unlocked_at"] is None for a in listing)

    locked = await client.put(
        f"{G}/achievements/equipped", json={"achievement_code": "night_owl"}, headers=who.headers
    )
    assert (locked.status_code, error_code(locked)) == (409, "ACHIEVEMENT_LOCKED")
    missing = await client.put(
        f"{G}/achievements/equipped", json={"achievement_code": "x"}, headers=who.headers
    )
    assert (missing.status_code, error_code(missing)) == (404, "ACHIEVEMENT_NOT_FOUND")

    await _exec(
        app,
        "INSERT INTO user_achievements (user_id, achievement_id, tier, source, unlocked_at, tier_reached_at) "
        "SELECT :u, id, 2, 'rule', now(), now() FROM achievements "
        "WHERE code IN ('night_owl', 'manhua_elite')",
        u=who.id,
    )
    ok = await client.put(
        f"{G}/achievements/equipped", json={"achievement_code": "night_owl"}, headers=who.headers
    )
    assert ok.status_code == 200 and ok.json()["achievement_code"] == "night_owl" and ok.json()["tier"] == 2
    assert (await _get(client, who, "/me"))["equipped_badge"]["code"] == "night_owl"
    again = await client.put(
        f"{G}/achievements/equipped", json={"achievement_code": "manhua_elite"}, headers=who.headers
    )
    assert again.status_code == 200
    listing = (await client.get(f"{G}/achievements", headers=who.headers)).json()
    assert [a["code"] for a in listing if a["equipped"]] == ["manhua_elite"]
    board = await _get(client, who, "/leaderboard")
    assert board["me"]["badge"]["code"] == "manhua_elite"

    still = await client.put(
        f"{G}/achievements/equipped", json={"achievement_code": "hsk3_master"}, headers=who.headers
    )
    assert still.status_code == 409
    assert (await _get(client, who, "/me"))["equipped_badge"]["code"] == "manhua_elite"

    cleared = await client.put(
        f"{G}/achievements/equipped", json={"achievement_code": None}, headers=who.headers
    )
    assert cleared.status_code == 200 and cleared.json()["achievement_code"] is None
    assert (await _get(client, who, "/me"))["equipped_badge"] is None


async def test_purge_minigame_rounds_job_deletes_old_rounds_and_keeps_sessions(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """F15.03: tác vụ dọn lượt mini-game chỉ xóa lượt phát quá 7 ngày; `minigame_sessions` không bị đụng."""
    from app.modules.gamification.application.public import PurgeMinigameRoundsUseCase

    who = await register(client)
    await _exec(
        app,
        "INSERT INTO minigame_rounds (id, user_id, mode, hsk_band, items, issued_at) VALUES "
        "(gen_random_uuid(), :u, 'hsk', 3, '[]'::jsonb, now() - interval '8 days'), "
        "(gen_random_uuid(), :u, 'hsk', 3, '[]'::jsonb, now() - interval '1 day')",
        u=who.id,
    )
    await _exec(
        app,
        "INSERT INTO minigame_sessions (user_id, game_type, target_radical, score, correct, wrong, "
        "duration_ms, played_at) VALUES "
        "(:u, 'pinyin_blade', 'x', 1, 1, 0, 1000, now() - interval '30 days')",
        u=who.id,
    )
    purge = PurgeMinigameRoundsUseCase(lambda: SqlGamificationUnitOfWork(app.state.container.session_factory))
    assert await purge.execute(datetime.now(timezone.utc)) >= 1
    left = await _scalar(app, "SELECT count(*) FROM minigame_rounds WHERE user_id = :u", u=who.id)
    kept = await _scalar(app, "SELECT count(*) FROM minigame_sessions WHERE user_id = :u", u=who.id)
    assert (left, kept) == (1, 1)


async def _tier_of(client: httpx.AsyncClient, who: Account, code: str) -> int:
    listing = (await client.get(f"{G}/achievements", headers=who.headers)).json()
    return int(next(a for a in listing if a["code"] == code)["tier"])


async def _first_tier_at_one(app: FastAPI, code: str) -> list[int]:
    """Hạ ngưỡng cấp I của huy hiệu về 1 để thử mở khóa tức thời; trả ngưỡng cũ để khôi phục."""
    async with app.state.container.session_factory() as session:
        old = (
            await session.execute(text("SELECT thresholds FROM achievements WHERE code = :c"), {"c": code})
        ).scalar_one()
        await session.execute(
            text("UPDATE achievements SET thresholds = ARRAY[1] WHERE code = :c"), {"c": code}
        )
        await session.commit()
    return list(old)


async def _restore_thresholds(app: FastAPI, code: str, thresholds: list[int]) -> None:
    await _exec(app, "UPDATE achievements SET thresholds = :t WHERE code = :c", t=thresholds, c=code)


async def test_hsk3_master_badge_unlocks_immediately_when_a_word_becomes_known(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-NH-91 / F16.11: đánh dấu "Đã thuộc" mở huy hiệu hsk3_master ngay, không chờ tác vụ nền 60 phút."""
    old = await _first_tier_at_one(app, "hsk3_master")
    try:
        who = await register(client)
        saved = await _save(client, who, BLOCK[0])
        assert saved.status_code == 201, saved.text
        entry_id = saved.json()["entry"]["id"]
        await _exec(app, "UPDATE vocab_entries SET hsk_level = 3 WHERE id = :i", i=entry_id)
        assert await _tier_of(client, who, "hsk3_master") == 0
        res = await client.patch(f"{VOCAB}/{entry_id}", json={"status": "known"}, headers=who.headers)
        assert res.status_code == 200, res.text
        assert await _tier_of(client, who, "hsk3_master") == 1
        kinds = [
            n["kind"]
            for n in (await client.get(f"{API}/notifications?size=50", headers=who.headers)).json()["items"]
        ]
        assert "achievement_unlocked" in kinds
    finally:
        await _restore_thresholds(app, "hsk3_master", old)


async def test_bubble_lookup_badge_unlocks_immediately_and_hover_survives_evaluation_failure(
    app: FastAPI, client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """US-NH-91 / F16.11: tra bong bóng mới mở huy hiệu ngay; đánh giá lỗi chỉ ghi log, tra vẫn thành công."""
    from app.modules.dictionary.application.use_cases.lookup_word import LookupWordUseCase
    from app.modules.dictionary.infrastructure.public import PypinyinProvider, SqlDictionaryUnitOfWork
    from app.modules.gamification.application.achievement_engine import AchievementEngine

    old = await _first_tier_at_one(app, "apprentice_translator")
    container = app.state.container
    try:
        who = await register(client)
        identity = Identity(user_id=who.id, role=Role.USER, session_id="s")
        lookup = LookupWordUseCase(
            lambda: SqlDictionaryUnitOfWork(container.session_factory), PypinyinProvider(), container.clock
        )
        await lookup.execute("你好", identity)  # không có bong bóng: không tính, không đánh giá
        assert await _tier_of(client, who, "apprentice_translator") == 0

        async def boom(*args: object, **kwargs: object) -> int:
            raise RuntimeError("đánh giá lỗi")

        with monkeypatch.context() as patched:
            patched.setattr(AchievementEngine, "evaluate", boom)
            result = await lookup.execute("你好", identity, bubble_id=90_001)
        assert result.term == "你好"  # lượt tra vẫn trả kết quả dù đánh giá huy hiệu lỗi
        assert await _tier_of(client, who, "apprentice_translator") == 0  # tác vụ nền sẽ bù

        await lookup.execute("你好", identity, bubble_id=90_002)
        assert await _tier_of(client, who, "apprentice_translator") == 1
        events = await _scalar(
            app, "SELECT count(*) FROM lookup_events WHERE user_id = :u AND bubble_id IS NOT NULL", u=who.id
        )
        assert events == 2
    finally:
        await _restore_thresholds(app, "apprentice_translator", old)


async def test_current_season_is_a_vietnam_week_created_once(client: httpx.AsyncClient) -> None:
    """US-NH-90: mùa tuần giờ VN, đếm ngược theo giờ máy chủ, ba bậc thưởng, yêu cầu cùng lúc chỉ một mùa."""
    who = await register(client)
    season = await _get(client, who, "/seasons/current")
    starts = _parse(season["starts_at"]).astimezone(VN_TZ)
    ends = _parse(season["ends_at"]).astimezone(VN_TZ)
    assert (starts.weekday(), starts.hour, starts.minute, starts.second) == (0, 0, 0, 0)
    assert ends - starts == timedelta(days=7) and season["number"] >= 1
    server_now = _parse(season["server_now"])
    assert abs((server_now - datetime.now(timezone.utc)).total_seconds()) < 60
    assert 0 < season["seconds_left"] <= 7 * 86400 and season["min_xp"] == 50
    tiers = {t["tier"]: t for t in season["tiers"]}
    assert (tiers["top3"]["rank_from"], tiers["top3"]["rank_to"], tiers["top3"]["vip_days"]) == (1, 3, 30)
    assert (tiers["top10"]["tickets"], tiers["top10"]["frame_code"]) == (3, "spring_petal")
    assert (tiers["top50"]["coins"], tiers["top50"]["badge_code"]) == (500, "seed_sower")
    assert season["my_rank"] is None and season["my_xp"] == 0 and season["my_tier"] is None

    others = [await register(client) for _ in range(3)]
    results = [await _get(client, o, "/seasons/current") for o in others]
    assert {r["id"] for r in results} == {season["id"]}
    history = await _get(client, who, "/seasons/me")
    assert history == {"items": [], "total": 0, "page": 1, "size": 20}


async def test_finalize_season_pays_each_tier_once_by_event_time_and_skips_locked(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    """US-HG-05, US-NH-90: xếp hạng theo thời điểm sự kiện (ranh giới 00:00 giờ VN), admin nhận thưởng, tài
    khoản khóa bị loại, chạy lại không trao hai lần, người dưới 50 XP không nhận."""
    container = app.state.container
    monday = date(2001, 1, 1) + timedelta(
        weeks=random.randrange(0, 900)
    )  # tuần xa trong quá khứ, không đụng dữ liệu thật
    start = datetime.combine(monday, time.min, VN_TZ)
    await _exec(app, "DELETE FROM seasons WHERE starts_at < '2019-01-01'")  # dọn mùa giả của lần chạy trước
    # XP giả còn sót ở tuần gần đó sẽ bị tác vụ chốt bù thành một mùa nữa, làm số người nhận thưởng gấp đôi.
    await _exec(app, "DELETE FROM xp_events WHERE created_at < '2019-01-01'")

    admin = await make_admin(app, client)
    first, second, third, fourth, tiny, locked = [await register(client) for _ in range(6)]
    fillers = [await register(client) for _ in range(7)]
    plan = [(first, 300), (admin, 250), (second, 200), (third, 100), (tiny, 40), (locked, 400)]
    plan += [(f, 90 - i) for i, f in enumerate(fillers)]  # hạng 5..11
    wednesday = (start + timedelta(days=2, hours=12)).astimezone(timezone.utc)
    for who, amount in plan:
        await _event(app, who.id, "quest", "seed", amount, wednesday)
    sunday_last_second = (start + timedelta(days=7) - timedelta(seconds=1)).astimezone(timezone.utc)
    next_monday = (start + timedelta(days=7)).astimezone(timezone.utc)
    await _event(app, fourth.id, "quest", "in-season", 60, sunday_last_second)
    await _event(app, fourth.id, "quest", "next-season", 500, next_monday)  # thuộc mùa sau, không được tính
    await client.post(
        f"{API}/admin/users/{locked.id}/lock", json={"reason": "Kiểm thử"}, headers=admin.headers
    )

    wallets = {
        w.id: (await client.get(f"{API}/rewards/wallet", headers=w.headers)).json()
        for w in (first, third, fourth)
    }
    now = (start + timedelta(days=8)).astimezone(timezone.utc)
    use_case = FinalizeSeasonsUseCase(
        lambda: SqlGamificationUnitOfWork(container.session_factory), container.notices
    )
    try:
        report = await use_case.execute(now)
        assert report.rewarded == {"top3": 3, "top10": 7, "top50": 2} and report.failed == 0, report
        assert report.seasons_finalized >= 1

        result = (await _get(client, first, "/seasons/me"))["items"][0]
        assert (result["rank"], result["xp"], result["tier"]) == (1, 300, "top3")
        assert result["reward_granted_at"] is not None
        after = (await client.get(f"{API}/rewards/wallet", headers=first.headers)).json()
        assert after["vip"]["days_left"] >= wallets[first.id]["vip"]["days_left"] + 29
        badges = {a["code"]: a for a in (await client.get(f"{G}/achievements", headers=first.headers)).json()}
        assert badges["top_scholar"]["tier"] == 1
        notices = (await client.get(f"{API}/notifications", headers=first.headers)).json()["items"]
        season_notice = next(n for n in notices if n["kind"] == "season_reward")
        assert season_notice["data"]["rank"] == 1 and season_notice["data"]["tier"] == "top3"

        admin_result = (await _get(client, admin, "/seasons/me"))["items"][0]
        assert (admin_result["rank"], admin_result["tier"]) == (2, "top3")  # admin được nhận thưởng mùa

        third_wallet = (await client.get(f"{API}/rewards/wallet", headers=third.headers)).json()
        assert third_wallet["ticket_balance"] == wallets[third.id]["ticket_balance"] + 3
        fourth_result = (await _get(client, fourth, "/seasons/me"))["items"][0]
        assert (fourth_result["rank"], fourth_result["xp"], fourth_result["tier"]) == (12, 60, "top50")
        fourth_wallet = (await client.get(f"{API}/rewards/wallet", headers=fourth.headers)).json()
        # 500 xu của bậc top50 + 50 xu của cấp I huy hiệu Người Gieo Hạt được trao kèm (F16.11).
        assert fourth_wallet["coin_balance"] == wallets[fourth.id]["coin_balance"] + 500 + 50
        fourth_badges = {
            a["code"]: a for a in (await client.get(f"{G}/achievements", headers=fourth.headers)).json()
        }
        assert fourth_badges["seed_sower"]["tier"] == 1

        assert (await _get(client, tiny, "/seasons/me"))["total"] == 0  # dưới 50 XP
        assert await _scalar(app, "SELECT count(*) FROM season_results WHERE user_id = :u", u=locked.id) == 0

        ledger_rows = await _scalar(
            app, "SELECT count(*) FROM wallet_ledger WHERE idempotency_key LIKE 'season:%'"
        )
        again = await use_case.execute(now)
        assert again.rewarded == {} and again.seasons_finalized == 0
        assert (
            await _scalar(app, "SELECT count(*) FROM wallet_ledger WHERE idempotency_key LIKE 'season:%'")
            == ledger_rows
        )
        assert (await _get(client, first, "/seasons/me"))["total"] == 1
        pending = await _scalar(
            app,
            "SELECT count(*) FROM season_results WHERE reward_granted_at IS NULL AND user_id = :u",
            u=first.id,
        )
        assert pending == 0
        status = await _scalar(
            app, "SELECT status FROM seasons WHERE starts_at = :s", s=start.astimezone(timezone.utc)
        )
        assert status == "finalized"
    finally:
        await _exec(app, "DELETE FROM seasons WHERE starts_at < '2019-01-01'")


async def _event(app: FastAPI, user_id: int, source: str, ref: str, amount: int, at: datetime) -> None:
    await _exec(
        app,
        "INSERT INTO xp_events (user_id, source, source_ref, amount, capped, activity_date, created_at) "
        "VALUES (:u, :s, :r, :a, false, :d, :at)",
        u=user_id,
        s=source,
        r=ref,
        a=amount,
        d=at.astimezone(VN_TZ).date(),
        at=at,
    )
