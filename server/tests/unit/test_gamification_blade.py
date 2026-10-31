"""M16 - Mini-game "Gõ pinyin chém chữ": đáp án pinyin, dựng bộ mục, chấm lại ở máy chủ (F16.01, US-NH-81)."""

from __future__ import annotations

import random
import uuid
from datetime import timedelta

import pytest

from app.modules.auth.application.public import Identity, Role
from app.modules.gamification.application.dto import (
    BuildRoundCommand,
    Notice,
    RoundView,
    SessionResult,
    SubmitRoundCommand,
)
from app.modules.gamification.application.use_cases.build_round import BuildRoundUseCase
from app.modules.gamification.application.use_cases.get_blade_best import GetBladeBestUseCase
from app.modules.gamification.application.use_cases.purge_minigame_rounds import PurgeMinigameRoundsUseCase
from app.modules.gamification.application.use_cases.submit_round import SubmitRoundUseCase
from app.modules.gamification.domain.blade_rules import (
    BOSS_MULTIPLIER,
    ITEMS_PER_ROUND,
    LIFE_BONUS,
    LIVES,
    MAX_EVENTS,
    MIN_KEY_MS,
    BladeEvent,
    band_levels,
    build_items,
    score_blade,
)
from app.modules.gamification.domain.entities import BladeItem, CharRow, MinigameRound, WordRow, XpSource
from app.modules.gamification.domain.errors import (
    InvalidMinigameRequestError,
    InvalidMinigameResultError,
    MinigameRoundExpiredError,
    MinigameRoundNotFoundError,
    MinigameRoundUsedError,
    NotEnoughCharsForGameError,
)
from app.modules.gamification.domain.minigame_rules import (
    GAME_SECONDS,
    ROUND_RETENTION_DAYS,
    ROUND_SUBMIT_GRACE_SECONDS,
)
from app.modules.gamification.domain.pinyin_answers import char_answers, word_answers
from tests.conftest import FixedClock
from tests.unit.gamification_fakes import FakeGamification, utc

ME = Identity(user_id=1, role=Role.USER, session_id="s")
OTHER = Identity(user_id=2, role=Role.USER, session_id="s")
NOW = utc(2026, 10, 28, 3)
STEP_MS = 200  # khoảng cách giữa hai hit trong test, đủ chậm với mọi đáp án


class _Notices:
    async def send(self, notice: Notice) -> None:
        return None


def _item(index: int, answers: tuple[str, ...] = ("ma",), boss: bool = False) -> BladeItem:
    return BladeItem(index, f"字{index}", "mā", answers, None, 1, boss)


def _hit(index: int, ms: int) -> BladeEvent:
    return BladeEvent(index, True, ms)


def _miss(index: int, ms: int) -> BladeEvent:
    return BladeEvent(index, False, ms)


def test_pinyin_answers_strip_tones_handle_umlaut_and_polyphones() -> None:
    """Đáp án a-z: bỏ dấu thanh, ü gõ là `u`, chữ đa âm nhận mọi âm, từ boss gõ liền."""
    assert char_answers("nǚ") == ["nu"]
    assert char_answers("lǜ") == ["lu"]
    assert char_answers("cè lu:è") == ["ce", "lue"]
    assert char_answers("le liǎo") == ["le", "liao"]
    assert char_answers("Ān") == ["an"]
    assert char_answers("xíng háng") == ["xing", "hang"]
    assert word_answers("lǜ sè") == ["luse"]
    assert word_answers("Běi jīng") == ["beijing"]
    assert word_answers("nǚ ér") == ["nuer"]


@pytest.mark.parametrize("raw", [None, "", "  ", "ma5", "m·a", "123"])
def test_pinyin_answers_drop_what_cannot_be_typed(raw: str | None) -> None:
    """Mục không dựng được đáp án a-z thì không có đáp án (bị bỏ khi dựng bộ)."""
    assert char_answers(raw) == [] and word_answers(raw) == []


def test_band_seven_covers_hsk_7_to_9() -> None:
    assert band_levels(3) == (3, 3)
    assert band_levels(7) == (7, 9)


def _chars(n: int) -> list[CharRow]:
    return [CharRow(chr(0x4E00 + i), "mā", f"vh{i}", 1) for i in range(n)]


def _words(n: int) -> list[WordRow]:
    return [WordRow(chr(0x5000 + i) + chr(0x5100 + i), "nǐ hǎo", 1) for i in range(n)]


def test_build_items_makes_100_unshuffled_free_unique_items_with_about_one_tenth_bosses() -> None:
    """100 mục, chữ không lặp khi đủ dữ liệu, boss hai chữ khoảng 1/10, chỉ số 0..99."""
    items = build_items(_chars(150), _words(30), random.Random(1))
    assert len(items) == ITEMS_PER_ROUND and [i.index for i in items] == list(range(ITEMS_PER_ROUND))
    assert len({i.text for i in items}) == ITEMS_PER_ROUND
    bosses = [i for i in items if i.is_boss]
    assert len(bosses) == ITEMS_PER_ROUND // 10 and all(len(b.text) == 2 for b in bosses)
    assert all(b.answers == ("nihao",) for b in bosses)
    assert all(not i.is_boss and len(i.text) == 1 for i in items if not i.is_boss)


def test_build_items_prefers_first_chars_skips_untypeable_and_repeats_only_when_short() -> None:
    """Chữ đứng đầu (chữ mới của cấp) được lấy trước; mục không có đáp án bị bỏ; thiếu thì lặp chữ."""
    many = _chars(300)
    items = build_items(many, [], random.Random(2))
    assert {i.text for i in items} == {c.ch for c in many[:ITEMS_PER_ROUND]}
    rows = [CharRow("坏", "?", None, 1), *_chars(25)]
    short = build_items(rows, [], random.Random(3))
    assert "坏" not in {i.text for i in short}
    assert len(short) == ITEMS_PER_ROUND and len({i.text for i in short}) == 25


def test_build_items_needs_at_least_twenty_distinct_items() -> None:
    with pytest.raises(NotEnoughCharsForGameError):
        build_items(_chars(19), [], random.Random(1))
    with pytest.raises(NotEnoughCharsForGameError):
        build_items([], _words(30), random.Random(1))
    assert len(build_items(_chars(10), _words(10), random.Random(1))) == ITEMS_PER_ROUND


def test_score_blade_applies_combo_multiplier_every_five_hits() -> None:
    """Mỗi hit 10 điểm, nhân 1 + 0,5 x (combo // 5): 4 hit đầu 10, hit thứ 5 được x1,5."""
    items = [_item(i) for i in range(5)]
    events = [_hit(i, (i + 1) * STEP_MS) for i in range(5)]
    result = score_blade(items, events, 0, 60_000)
    assert (result.score - LIFE_BONUS * LIVES, result.hits, result.max_combo) == (4 * 10 + 15, 5, 5)


def test_score_blade_combo_multiplier_is_capped_at_triple() -> None:
    items = [_item(i) for i in range(25)]
    events = [_hit(i, (i + 1) * STEP_MS) for i in range(25)]
    result = score_blade(items, events, 0, 60_000)
    # 4 hit x10, 5 hit x15, 5 hit x20, 5 hit x25, từ hit thứ 20 trần x30: 40 + 75 + 100 + 125 + 6 x 30.
    assert result.score == 520 + LIFE_BONUS * LIVES and result.max_combo == 25  # hết bộ mục: thưởng mạng


def test_score_blade_boss_scores_triple_and_miss_resets_combo_and_costs_a_life() -> None:
    items = [_item(0), _item(1, ("nihao",), boss=True), _item(2), _item(3)]
    events = [_hit(0, 200), _hit(1, 600), _miss(2, 700), _hit(3, 900)]
    result = score_blade(items, events, 0, 60_000)
    # hit 10 + boss 10 x3 (combo 2) + miss + hit 10 (combo về 1); hết bộ mục còn 2 mạng: +10.
    assert result.score == 10 + 10 * BOSS_MULTIPLIER + 10 + 2 * LIFE_BONUS
    assert (result.max_combo, result.lives_left, result.misses) == (2, 2, 1)
    assert [m.index for m in result.missed] == [2]


def test_score_blade_gives_no_life_bonus_when_ended_early() -> None:
    items = [_item(i) for i in range(5)]
    result = score_blade(items, [_hit(0, 200), _hit(1, 400)], 0, 60_000)
    assert result.score == 20 and result.lives_left == LIVES


def test_score_blade_accuracy_counts_shortest_answer_keys_over_typos() -> None:
    """Chính xác = phím đúng (đáp án ngắn nhất của các hit) / (phím đúng + gõ sai)."""
    items = [_item(0, ("ma", "maa")), _item(1, ("xiang",))]
    result = score_blade(items, [_hit(0, 200), _hit(1, 800)], 3, 60_000)
    assert result.accuracy == round(7 / 10, 4)
    assert score_blade(items, [], 0, 60_000).accuracy == 0.0


@pytest.mark.parametrize(
    ("hits", "typos", "rank"),
    [(80, 0, "S"), (80, 10, "A"), (80, 30, "B"), (50, 0, "A"), (25, 0, "B"), (10, 0, "C"), (80, 200, "C")],
)
def test_score_blade_rank_depends_on_hits_and_accuracy(hits: int, typos: int, rank: str) -> None:
    items = [_item(i) for i in range(ITEMS_PER_ROUND)]
    events = [_hit(i, (i + 1) * STEP_MS) for i in range(hits)]
    assert score_blade(items, events, typos, 120_000).rank == rank


def test_score_blade_score_is_clamped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.gamification.domain.blade_rules.MAX_SCORE", 50)
    items = [_item(i) for i in range(10)]
    events = [_hit(i, (i + 1) * STEP_MS) for i in range(10)]
    assert score_blade(items, events, 0, 60_000).score == 50


def test_score_blade_lists_missed_items_in_play_order() -> None:
    items = [_item(i) for i in range(5)]
    result = score_blade(items, [_miss(2, 100), _hit(0, 400), _miss(4, 600)], 0, 60_000)
    assert [m.index for m in result.missed] == [2, 4]


@pytest.mark.parametrize(
    "events",
    [
        [_hit(99, 500)],  # chỉ số không có trong ván
        [_hit(-1, 500)],
        [_hit(0, 300), _hit(0, 900)],  # lặp mục
        [_hit(0, 900), _hit(1, 400)],  # mốc thời gian lùi
        [_hit(0, 90_000)],  # vượt thời gian máy chủ đo
        [_hit(0, 10)],  # gõ nhanh hơn người thật (2 phím x 35 ms)
        [_hit(0, 300), _hit(1, 300 + MIN_KEY_MS)],
        [_miss(0, 100), _miss(1, 200), _miss(2, 300), _hit(3, 800)],  # chơi tiếp sau khi hết mạng
    ],
)
def test_score_blade_rejects_implausible_event_chains(events: list[BladeEvent]) -> None:
    with pytest.raises(InvalidMinigameResultError):
        score_blade([_item(i) for i in range(5)], events, 0, 60_000)


def test_score_blade_rejects_too_many_events_and_negative_typos() -> None:
    items = [_item(i) for i in range(MAX_EVENTS + 1)]
    with pytest.raises(InvalidMinigameResultError):
        score_blade(items, [_miss(i, i) for i in range(MAX_EVENTS + 1)], 0, 60_000)
    with pytest.raises(InvalidMinigameResultError):
        score_blade(items, [], -1, 60_000)


class _Game:
    """Một người chơi giả: phát lượt rồi nộp, đồng hồ chạy được."""

    def __init__(self) -> None:
        self.store = FakeGamification()
        self.store.chars.char_rows = _chars(150)
        self.store.chars.word_rows = _words(30)
        self.clock = FixedClock(NOW)
        self.builder = BuildRoundUseCase(lambda: self.store, self.clock, random.Random(1))  # type: ignore[arg-type,return-value]
        self.submit = SubmitRoundUseCase(lambda: self.store, _Notices(), self.clock)  # type: ignore[arg-type,return-value]

    async def new_round(self, who: Identity = ME, band: int | None = 3) -> RoundView:
        command = (
            BuildRoundCommand("hsk", band, None)
            if band is not None
            else BuildRoundCommand("weak_radical", None, "氵")
        )
        return await self.builder.execute(who, command)

    def hit_all(self, view: RoundView, count: int | None = None) -> list[BladeEvent]:
        picked = view.items[: count or len(view.items)]
        return [_hit(item.index, (n + 1) * STEP_MS) for n, item in enumerate(picked)]

    def command(
        self, view: RoundView, events: list[BladeEvent], duration_ms: int = 30_000
    ) -> SubmitRoundCommand:
        return SubmitRoundCommand(view.round_id, events, 0, duration_ms)

    async def play(self, hits: int, band: int | None = 3, who: Identity = ME) -> SessionResult:
        """Phát lượt, để đồng hồ máy chủ chạy 60 giây rồi nộp `hits` hit liên tiếp."""
        view = await self.new_round(who, band)
        self.clock.at += timedelta(seconds=60)
        return await self.submit.execute(who, self.command(view, self.hit_all(view, hits)))


async def test_build_round_stores_items_with_answers_and_rejects_bad_requests() -> None:
    """Lượt lưu đủ 100 mục kèm đáp án; thiếu cấp/bộ thủ → INVALID_MINIGAME_REQUEST; thiếu dữ liệu → 409."""
    game = _Game()
    view = await game.new_round(band=3)
    saved = game.store.minigames.rounds[view.round_id]
    assert (saved.user_id, saved.mode, saved.hsk_band, saved.radical, saved.issued_at) == (
        1,
        "hsk",
        3,
        None,
        NOW,
    )
    assert saved.items == view.items and len(view.items) == ITEMS_PER_ROUND
    assert (view.seconds, view.lives) == (GAME_SECONDS, LIVES) and view.seconds == 120
    weak = await game.new_round(band=None)
    assert (weak.mode, weak.hsk_band, weak.radical) == ("weak_radical", None, "氵")
    for bad in (
        BuildRoundCommand("hsk", None, None),
        BuildRoundCommand("hsk", 8, None),
        BuildRoundCommand("hsk", 0, None),
        BuildRoundCommand("weak_radical", None, None),
        BuildRoundCommand("weak_radical", None, ""),
        BuildRoundCommand("khac", 3, None),
    ):
        with pytest.raises(InvalidMinigameRequestError):
            await game.builder.execute(ME, bad)
    game.store.chars.char_rows = _chars(5)
    game.store.chars.word_rows = []
    with pytest.raises(NotEnoughCharsForGameError):
        await game.new_round(band=3)
    assert len(game.store.minigames.rounds) == 2  # lượt thiếu dữ liệu không được lưu


async def test_submit_scores_on_server_adds_xp_in_same_transaction_and_stores_server_duration() -> None:
    """Máy chủ tự chấm: 100 hit liên tiếp; XP = min(10, hit // 2); thời gian lưu không vượt số đo máy chủ."""
    game = _Game()
    view = await game.new_round()
    game.clock.at = NOW + timedelta(seconds=40)
    result = await game.submit.execute(ME, game.command(view, game.hit_all(view), duration_ms=90_000))
    assert (result.correct, result.wrong, result.max_combo, result.xp_awarded) == (100, 0, 100, 10)
    assert result.mode == "hsk" and result.hsk_band == 3 and result.rank == "S"
    assert game.store.xp.rows[(1, XpSource.MINIGAME, str(result.id))].amount == 10
    assert result.duration_ms == 40_000  # không vượt số đo của máy chủ dù trình duyệt báo 90 giây
    assert result.is_best is True and result.accuracy == 1.0


async def test_submit_xp_is_half_of_hits_and_only_five_games_per_day_count() -> None:
    game = _Game()
    awarded = [(await game.play(hits)).xp_awarded for hits in (7, 2, 100, 100, 100, 100)]
    assert awarded == [3, 1, 10, 10, 10, 0]


async def test_submit_is_best_compares_with_same_band_only() -> None:
    game = _Game()
    assert (await game.play(10)).is_best is True
    assert (await game.play(5)).is_best is False
    assert (await game.play(30)).is_best is True
    assert (await game.play(3, band=4)).is_best is True
    assert (await game.play(3, band=None)).is_best is True


async def test_submit_returns_missed_items_for_review() -> None:
    game = _Game()
    view = await game.new_round()
    events = [_hit(view.items[0].index, 200), _miss(view.items[1].index, 400)]
    result = await game.submit.execute(ME, game.command(view, events))
    second = view.items[1]
    assert (result.wrong, result.correct) == (1, 1)
    assert [(m.text, m.pinyin, m.han_viet) for m in result.missed] == [
        (second.text, second.pinyin, second.han_viet)
    ]


async def test_submit_rejects_forged_chain_without_burning_the_round() -> None:
    """Chuỗi sự kiện giả → 400, lượt chưa nộp, không ván, không XP."""
    game = _Game()
    view = await game.new_round()
    with pytest.raises(InvalidMinigameResultError):
        await game.submit.execute(ME, game.command(view, [_hit(500, 400)]))
    with pytest.raises(InvalidMinigameResultError):  # ms giảm
        await game.submit.execute(ME, game.command(view, [_hit(0, 900), _hit(1, 400)]))
    with pytest.raises(InvalidMinigameResultError):  # bot gõ quá nhanh
        await game.submit.execute(ME, game.command(view, [_hit(0, 5)]))
    assert game.store.minigames.sessions == [] and game.store.xp.rows == {}
    assert game.store.minigames.rounds[view.round_id].submitted_at is None
    assert (await game.submit.execute(ME, game.command(view, game.hit_all(view, 3)))).correct == 3


async def test_submit_rejects_round_twice_other_users_and_unknown_rounds() -> None:
    game = _Game()
    view = await game.new_round()
    with pytest.raises(MinigameRoundNotFoundError):
        await game.submit.execute(OTHER, game.command(view, game.hit_all(view, 3)))
    await game.submit.execute(ME, game.command(view, game.hit_all(view, 3)))
    with pytest.raises(MinigameRoundUsedError):
        await game.submit.execute(ME, game.command(view, game.hit_all(view, 3)))
    assert len(game.store.minigames.sessions) == 1
    with pytest.raises(MinigameRoundNotFoundError):
        await game.submit.execute(ME, SubmitRoundCommand(uuid.uuid4(), [], 0, 5_000))


async def test_submit_rejects_expired_round_and_implausible_client_duration() -> None:
    game = _Game()
    view = await game.new_round()
    for bad in (500, 130_000):
        with pytest.raises(InvalidMinigameResultError):
            await game.submit.execute(ME, game.command(view, game.hit_all(view, 3), bad))
    game.clock.at = NOW + timedelta(seconds=GAME_SECONDS + ROUND_SUBMIT_GRACE_SECONDS, milliseconds=1)
    with pytest.raises(MinigameRoundExpiredError):
        await game.submit.execute(ME, game.command(view, game.hit_all(view, 3)))
    assert game.store.minigames.sessions == [] and game.store.xp.rows == {}
    game.clock.at = NOW + timedelta(seconds=GAME_SECONDS + ROUND_SUBMIT_GRACE_SECONDS)  # đúng hạn thì nhận
    assert (await game.submit.execute(ME, game.command(view, game.hit_all(view, 3)))).correct == 3


async def test_submit_concurrent_double_submit_is_accepted_once() -> None:
    """Hai yêu cầu cùng lượt chỉ một được nhận ở mức kho (đánh dấu có điều kiện trả False)."""
    game = _Game()
    view = await game.new_round()
    repo = game.store.minigames
    assert await repo.mark_round_submitted(view.round_id, NOW) is True
    assert await repo.mark_round_submitted(view.round_id, NOW) is False


async def test_blade_best_groups_by_band_for_the_caller_only() -> None:
    game = _Game()
    for band, hits in ((3, 10), (3, 30), (5, 4), (None, 6)):
        await game.play(hits, band)
    await game.play(50, 3, OTHER)
    best = await GetBladeBestUseCase(lambda: game.store).execute(ME)  # type: ignore[arg-type,return-value]
    assert [(b.mode, b.hsk_band, b.plays) for b in best] == [
        ("hsk", 3, 2),
        ("hsk", 5, 1),
        ("weak_radical", None, 1),
    ]
    assert best[0].best_score > best[1].best_score > 0 and best[0].best_combo == 30


async def test_purge_minigame_rounds_removes_only_rounds_older_than_retention_in_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F15.03: lượt quá 7 ngày bị xóa theo lô; lượt mới và lịch sử ván (`minigame_sessions`) được giữ."""
    monkeypatch.setattr(
        "app.modules.gamification.application.use_cases.purge_minigame_rounds.ROUND_PURGE_BATCH_SIZE", 2
    )
    game = _Game()
    old_view = await game.new_round()
    await game.submit.execute(ME, game.command(old_view, game.hit_all(old_view, 3)))  # tạo một ván
    game.clock.at = NOW + timedelta(days=ROUND_RETENTION_DAYS + 1)
    fresh = await game.new_round()
    for _ in range(4):
        await game.store.minigames.add_round(
            MinigameRound(uuid.uuid4(), 1, "hsk", 3, None, [_item(0)], NOW + timedelta(seconds=1), None)
        )
    purge = PurgeMinigameRoundsUseCase(lambda: game.store)  # type: ignore[arg-type,return-value]
    assert await purge.execute(game.clock.at) == 5  # 5 lượt cũ (1 đã nộp + 4), qua 3 lô
    assert set(game.store.minigames.rounds) == {fresh.round_id}
    assert len(game.store.minigames.sessions) == 1
    assert await purge.execute(game.clock.at) == 0
