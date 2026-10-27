"""M08 — domain và use case với repository giả: F08.01, F08.02, F08.03, F08.05, F08.06, F08.07, F08.09."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.modules.review.application.dto import GradeCommand
from app.modules.review.application.sides import sides_for
from app.modules.review.application.use_cases.create_cards_for_entry import CreateCardsForEntryUseCase
from app.modules.review.application.use_cases.get_card_history import GetCardHistoryUseCase
from app.modules.review.application.use_cases.get_due_cards import GetDueCardsUseCase
from app.modules.review.application.use_cases.get_review_summary import GetReviewSummaryUseCase
from app.modules.review.application.use_cases.grade_card import GradeCardUseCase
from app.modules.review.application.use_cases.reset_card import ResetCardUseCase
from app.modules.review.application.use_cases.resume_card import ResumeCardUseCase
from app.modules.review.application.use_cases.suspend_card import SuspendCardUseCase
from app.modules.review.domain.entities import CardState, CardType, DeckKind, Rating
from app.modules.review.domain.errors import (
    CardNotFoundError,
    CardSuspendedError,
    InvalidDeckError,
    InvalidRatingError,
    PresentationIdTakenError,
)
from app.modules.review.domain.rules import local_day_bounds, parse_deck, parse_rating
from app.modules.review.infrastructure.fsrs_scheduler import FsrsScheduler
from tests.conftest import FixedClock
from tests.unit.review_fakes import FakeReviewUow, FakeVocabSource, identity

NOW = datetime(2026, 10, 24, 8, 0, tzinfo=timezone.utc)


def _scheduler() -> FsrsScheduler:
    return FsrsScheduler(enable_fuzzing=False)  # kết quả xác định để so sánh khoảng cách ôn


async def _uow_with_cards(entry_id: int = 1, user_id: int = 1) -> FakeReviewUow:
    uow = FakeReviewUow()
    uow.vocab.add_face(entry_id)
    await CreateCardsForEntryUseCase(_scheduler()).execute(uow.cards, user_id, entry_id, NOW)
    return uow


def _grade_uc(uow: FakeReviewUow, clock: FixedClock) -> GradeCardUseCase:
    return GradeCardUseCase(lambda: uow, _scheduler(), clock)


def _command(card_id: int, rating: int, presentation: uuid.UUID | None = None) -> GradeCommand:
    return GradeCommand(card_id, rating, presentation or uuid.uuid4())


async def test_create_cards_makes_three_new_cards_due_at_save_time() -> None:
    """F08.09, US-NH-40 TC5: mỗi từ có đủ ba loại thẻ, trạng thái FSRS mới, đến hạn ngay lúc lưu."""
    uow = await _uow_with_cards()
    cards = list(uow.cards.items.values())
    assert {c.card_type for c in cards} == set(CardType)
    for card in cards:
        assert card.schedule.state is CardState.LEARNING
        assert card.schedule.due_at == NOW
        assert (card.reps, card.lapses, card.is_suspended) == (0, 0, False)
        assert card.schedule.stability is None


async def test_due_cards_include_only_due_active_cards_oldest_first() -> None:
    """F08.01: thẻ có hạn ở tương lai và thẻ tạm ngưng không xuất hiện; quá hạn lâu nhất trước."""
    uow = await _uow_with_cards()
    cards = list(uow.cards.items.values())
    cards[0].schedule = replace(cards[0].schedule, due_at=NOW + timedelta(hours=1))  # tương lai
    cards[1].is_suspended = True
    cards[2].schedule = replace(cards[2].schedule, due_at=NOW - timedelta(days=2))
    batch = await GetDueCardsUseCase(lambda: uow, FixedClock(NOW)).execute(identity(), 20, None)
    assert [d.card.id for d in batch.cards] == [cards[2].id]
    assert batch.total == 1


async def test_due_cards_exclude_known_and_ignored_words() -> None:
    """F08.01, US-NH-33: thẻ của từ "Đã thuộc"/"Bỏ qua" không đến hạn dù đã qua hạn."""
    uow = await _uow_with_cards(entry_id=1)
    await CreateCardsForEntryUseCase(_scheduler()).execute(uow.cards, 1, 2, NOW)
    uow.vocab.add_face(2, term="再见")
    uow.cards.learning = {1}  # từ 2 đã chuyển sang "Đã thuộc"
    batch = await GetDueCardsUseCase(lambda: uow, FixedClock(NOW)).execute(identity(), 20, None)
    assert {d.card.vocab_entry_id for d in batch.cards} == {1}
    assert batch.total == 3


async def test_due_cards_never_return_other_users_cards() -> None:
    uow = await _uow_with_cards(user_id=2)
    batch = await GetDueCardsUseCase(lambda: uow, FixedClock(NOW)).execute(identity(1), 20, None)
    assert batch.total == 0 and batch.cards == []


async def test_due_cards_filter_by_deck_and_reject_bad_deck() -> None:
    uow = await _uow_with_cards(entry_id=1)
    await CreateCardsForEntryUseCase(_scheduler()).execute(uow.cards, 1, 2, NOW)
    uow.vocab.add_face(2, term="再见")
    uow.vocab.decks["starred"] = [2]
    usecase = GetDueCardsUseCase(lambda: uow, FixedClock(NOW))
    batch = await usecase.execute(identity(), 20, "starred")
    assert {d.card.vocab_entry_id for d in batch.cards} == {2} and batch.deck.kind is DeckKind.STARRED
    assert (await usecase.execute(identity(), 20, "series:99")).total == 0
    with pytest.raises(InvalidDeckError):
        await usecase.execute(identity(), 20, "series:abc")


@pytest.mark.parametrize("rating", [1, 2, 3, 4])
async def test_grade_each_rating_updates_card_and_writes_review_log(rating: int) -> None:
    """F08.02, US-NH-39: bốn mức đánh giá đều cập nhật thẻ và ghi lượt ôn trong một giao dịch."""
    uow = await _uow_with_cards()
    card = next(iter(uow.cards.items.values()))
    clock = FixedClock(NOW)
    result = await _grade_uc(uow, clock).execute(identity(), _command(card.id, rating))
    assert uow.commits == 1 and len(uow.logs.items) == 1
    log = uow.logs.items[0]
    assert (log.rating, log.state_before, log.reviewed_at) == (Rating(rating), CardState.LEARNING, NOW)
    assert log.due_after == result.due_at == uow.cards.items[card.id].schedule.due_at
    assert uow.cards.items[card.id].reps == 1
    assert uow.cards.items[card.id].schedule.last_review_at == NOW
    assert result.due_at > NOW and not result.duplicate


async def test_grade_buries_due_sibling_cards_of_the_same_word_until_next_day() -> None:
    """F08.02: chấm một thẻ thì các thẻ khác của cùng từ đang đến hạn dời sang đầu ngày mai, giữ S và D."""
    uow = await _uow_with_cards()
    graded = next(iter(uow.cards.items.values()))
    siblings = [
        c for c in uow.cards.items.values() if c.vocab_entry_id == graded.vocab_entry_id and c.id != graded.id
    ]
    before = {c.id: (c.schedule.stability, c.schedule.difficulty) for c in siblings}
    await _grade_uc(uow, FixedClock(NOW)).execute(identity(), _command(graded.id, 3))
    tomorrow = local_day_bounds(NOW, None)[1]
    assert siblings and all(c.schedule.due_at == tomorrow for c in siblings)
    assert all((c.schedule.stability, c.schedule.difficulty) == before[c.id] for c in siblings)
    assert len(uow.logs.items) == 1  # dời thẻ không phải lượt ôn


async def test_grade_easy_schedules_further_than_again() -> None:
    """F08.02 quy tắc: khoảng cách khi chọn "Dễ" dài hơn khi chọn "Quên" (cùng một thẻ)."""
    again_uow, easy_uow = await _uow_with_cards(), await _uow_with_cards()
    clock = FixedClock(NOW)
    again = await _grade_uc(again_uow, clock).execute(identity(), _command(1, Rating.AGAIN))
    easy = await _grade_uc(easy_uow, clock).execute(identity(), _command(1, Rating.EASY))
    assert easy.interval_seconds > again.interval_seconds > 0


async def test_grade_double_click_with_same_presentation_counts_once() -> None:
    """F08.02: một lượt hiển thị chỉ tính một lượt ôn, kể cả khi bấm đúp."""
    uow = await _uow_with_cards()
    clock = FixedClock(NOW)
    presentation = uuid.uuid4()
    first = await _grade_uc(uow, clock).execute(identity(), _command(1, 3, presentation))
    due_after_first = uow.cards.items[1].schedule.due_at
    clock.at = NOW + timedelta(seconds=2)
    second = await _grade_uc(uow, clock).execute(identity(), _command(1, 3, presentation))
    assert len(uow.logs.items) == 1 and uow.cards.items[1].reps == 1
    assert uow.cards.items[1].schedule.due_at == due_after_first
    assert second.duplicate and not first.duplicate and second.due_at == first.due_at


async def test_grade_presentation_used_for_another_card_is_rejected() -> None:
    uow = await _uow_with_cards()
    clock = FixedClock(NOW)
    presentation = uuid.uuid4()
    await _grade_uc(uow, clock).execute(identity(), _command(1, 3, presentation))
    with pytest.raises(PresentationIdTakenError):
        await _grade_uc(uow, clock).execute(identity(), _command(2, 3, presentation))


async def test_grade_other_users_card_is_not_found_and_suspended_card_is_rejected() -> None:
    uow = await _uow_with_cards(user_id=2)
    clock = FixedClock(NOW)
    with pytest.raises(CardNotFoundError):
        await _grade_uc(uow, clock).execute(identity(1), _command(1, 3))
    uow.cards.items[1].is_suspended = True
    with pytest.raises(CardSuspendedError):
        await _grade_uc(uow, clock).execute(identity(2), _command(1, 3))
    assert uow.logs.items == [] and uow.commits == 0


async def test_grade_returns_next_card_or_session_complete() -> None:
    """F08.02, F08.07: sau khi chấm trả thẻ kế tiếp; hết thẻ đến hạn thì báo hoàn thành."""
    uow = await _uow_with_cards()
    clock = FixedClock(NOW)
    ids = sorted(uow.cards.items)
    first = await _grade_uc(uow, clock).execute(identity(), _command(ids[0], 4))
    # Ba thẻ cùng một từ: chấm một thẻ thì hai thẻ kia dời sang ngày mai nên phiên ôn hết thẻ.
    assert first.next_batch.total == 0 and first.next_batch.cards == []
    await _grade_uc(uow, clock).execute(identity(), _command(ids[1], 4))
    last = await _grade_uc(uow, clock).execute(identity(), _command(ids[2], 4))
    assert last.next_batch.total == 0 and last.next_batch.cards == []


async def test_grade_again_on_review_card_counts_a_lapse() -> None:
    uow = await _uow_with_cards()
    clock = FixedClock(NOW)
    await _grade_uc(uow, clock).execute(identity(), _command(1, 4))  # Easy → thẻ sang trạng thái ôn
    assert uow.cards.items[1].schedule.state is CardState.REVIEW
    clock.at = NOW + timedelta(days=30)
    await _grade_uc(uow, clock).execute(identity(), _command(1, 1))
    assert uow.cards.items[1].lapses == 1
    assert uow.cards.items[1].schedule.state is CardState.RELEARNING


def test_parse_rating_accepts_only_one_to_four() -> None:
    assert [parse_rating(i) for i in (1, 2, 3, 4)] == list(Rating)
    for bad in (0, 5, -1, True, 2.0, "3", None):
        with pytest.raises(InvalidRatingError):
            parse_rating(bad)


def test_parse_deck_keys() -> None:
    assert parse_deck(None).kind is DeckKind.ALL and parse_deck("all").kind is DeckKind.ALL
    assert parse_deck("starred").key == "starred"
    deck = parse_deck("series:12")
    assert (deck.kind, deck.series_id, deck.key) == (DeckKind.SERIES, 12, "series:12")
    for bad in ("series:", "series:0", "series:x", "foo"):
        with pytest.raises(InvalidDeckError):
            parse_deck(bad)


def test_local_day_bounds_follow_learner_timezone() -> None:
    """F08.01: "hôm nay" theo múi giờ của người học."""
    now = datetime(2026, 10, 24, 18, 30, tzinfo=timezone.utc)  # 01:30 ngày 25 ở Việt Nam
    start, end = local_day_bounds(now, "Asia/Ho_Chi_Minh")
    assert start == datetime(2026, 10, 24, 17, 0, tzinfo=timezone.utc)
    assert end - start == timedelta(days=1)
    utc_start, _ = local_day_bounds(now, None)
    assert utc_start == datetime(2026, 10, 24, tzinfo=timezone.utc)
    assert local_day_bounds(now, "Khong/Ton_Tai")[0] == utc_start


def test_card_sides_follow_card_type() -> None:
    """F08.03: nhận diện Hán→Việt, nhớ lại Việt→Hán, nghe: mặt trước không lộ chữ Hán."""
    source = FakeVocabSource()
    source.add_face(1)
    face = source.faces_by_id[1]
    front, back = sides_for(CardType.RECOGNITION, face)
    assert (front.term, front.meaning_vi) == ("你好", None) and back.meaning_vi == "xin chào"
    front, back = sides_for(CardType.RECALL, face)
    assert (front.term, front.meaning_vi) == (None, "xin chào") and (back.term, back.pinyin) == (
        "你好",
        "nǐ hǎo",
    )
    front, back = sides_for(CardType.LISTENING, face)
    assert (front.term, front.audio_text) == (None, "你好") and back.term == "你好"


def test_recall_front_falls_back_when_meaning_is_missing() -> None:
    """F08.03: thiếu nghĩa -> câu dịch ngữ cảnh -> Hán Việt -> pinyin; luôn ghi nguồn gợi ý."""
    source = FakeVocabSource()
    source.add_face(1)
    face = replace(source.faces_by_id[1], meaning_vi=None)
    front, _ = sides_for(CardType.RECALL, face)
    assert (front.hint_source, front.sentence_vi, front.meaning_vi) == (
        "context_sentence",
        "Bạn khỏe không",
        None,
    )
    assert front.term is None
    no_sentence = replace(face, context=replace(face.context, sentence_vi=None) if face.context else None)
    front, _ = sides_for(CardType.RECALL, no_sentence)
    assert (front.hint_source, front.sino_vietnamese) == ("sino_vietnamese", "nhĩ hảo")
    front, _ = sides_for(CardType.RECALL, replace(no_sentence, sino_vietnamese=None))
    assert (front.hint_source, front.pinyin) == ("pinyin", "nǐ hǎo")
    front, _ = sides_for(CardType.RECALL, replace(no_sentence, sino_vietnamese=None, pinyin=None))
    assert front.hint_source is None
    full_front, _ = sides_for(CardType.RECALL, source.faces_by_id[1])
    assert (full_front.hint_source, full_front.meaning_vi) == ("meaning", "xin chào")
    assert sides_for(CardType.RECOGNITION, face)[0].hint_source is None


async def test_suspend_resume_and_reset_keep_history() -> None:
    """F08.05, US-NH-42: tạm ngưng/tiếp tục đổi cờ; đặt lại đưa S, D về thẻ mới nhưng giữ lịch sử ôn."""
    uow = await _uow_with_cards()
    clock = FixedClock(NOW)
    await _grade_uc(uow, clock).execute(identity(), _command(1, 3))
    card = uow.cards.items[1]
    assert card.schedule.stability is not None

    suspended = await SuspendCardUseCase(lambda: uow, clock).execute(identity(), 1)
    assert suspended.is_suspended
    assert (
        await GetDueCardsUseCase(lambda: uow, FixedClock(NOW + timedelta(days=9))).execute(
            identity(), 20, None
        )
    ).total == 2
    resumed = await ResumeCardUseCase(lambda: uow, clock).execute(identity(), 1)
    assert not resumed.is_suspended

    clock.at = NOW + timedelta(days=1)
    reset = await ResetCardUseCase(lambda: uow, _scheduler(), clock).execute(identity(), 1)
    assert reset.schedule.stability is None and reset.schedule.difficulty is None
    assert reset.schedule.state is CardState.LEARNING and reset.schedule.due_at == clock.at
    assert (reset.reps, reset.lapses) == (0, 0)
    assert len(uow.logs.items) == 1  # lịch sử còn nguyên


async def test_card_actions_on_other_users_card_are_not_found() -> None:
    uow = await _uow_with_cards(user_id=2)
    clock = FixedClock(NOW)
    for usecase in (SuspendCardUseCase(lambda: uow, clock), ResumeCardUseCase(lambda: uow, clock)):
        with pytest.raises(CardNotFoundError):
            await usecase.execute(identity(1), 1)
    with pytest.raises(CardNotFoundError):
        await ResetCardUseCase(lambda: uow, _scheduler(), clock).execute(identity(1), 1)
    with pytest.raises(CardNotFoundError):
        await GetCardHistoryUseCase(lambda: uow).execute(identity(1), 1, 1, 20)


async def test_history_is_paged_newest_first() -> None:
    """F08.06, US-NH-43."""
    uow = await _uow_with_cards()
    clock = FixedClock(NOW)
    for step in range(3):
        clock.at = NOW + timedelta(days=step * 10)
        await _grade_uc(uow, clock).execute(identity(), _command(1, 3))
    page = await GetCardHistoryUseCase(lambda: uow).execute(identity(), 1, 1, 2)
    assert page.total == 3 and len(page.items) == 2
    assert page.items[0].reviewed_at > page.items[1].reviewed_at
    assert (await GetCardHistoryUseCase(lambda: uow).execute(identity(), 2, 1, 20)).total == 0


class _Tz:
    async def timezone_of(self, identity: object, owner_id: int) -> str | None:
        return "Asia/Ho_Chi_Minh"


async def test_summary_distinguishes_no_cards_due_and_completed() -> None:
    """F08.07, US-NH-44."""
    empty = FakeReviewUow()
    clock = FixedClock(NOW)
    summary = GetReviewSummaryUseCase(lambda: empty, _Tz(), clock)
    assert (await summary.execute(identity())).status == "no_cards"

    uow = await _uow_with_cards()
    summary = GetReviewSummaryUseCase(lambda: uow, _Tz(), clock)
    due_summary = await summary.execute(identity())
    assert due_summary.status == "due"
    assert due_summary.due_words == 1 and due_summary.status_counts["learning"] == 1
    for card_id in sorted(uow.cards.items):
        await _grade_uc(uow, clock).execute(identity(), _command(card_id, 3))
    done = await summary.execute(identity())
    assert (done.status, done.reviewed_today, done.due_now, done.timezone) == (
        "completed",
        3,
        0,
        "Asia/Ho_Chi_Minh",
    )
    assert done.next_due_at is not None and done.next_due_at > NOW
    assert done.due_later_today >= 0
