"""Nhiệm vụ ngày (F16.04): tiến độ tính khi gọi từ `daily_activities` và sổ XP, không có bảng riêng."""

from __future__ import annotations

from datetime import date, datetime

from app.core.learning_events import LearningSource
from app.modules.gamification.application.dto import QuestsToday, QuestView
from app.modules.gamification.application.ports import GamificationStore
from app.modules.gamification.domain.entities import NewXpEvent, XpSource
from app.modules.gamification.domain.xp_rules import (
    QUEST_ALL_BONUS_COINS,
    QUESTS,
    quest_ref,
    quests_all_key,
)
from app.modules.rewards.application.public import LedgerReason, RewardBundle


async def award_xp(
    store: GamificationStore, user_id: int, source: XpSource, ref: str, amount: int, day: date, now: datetime
) -> bool:
    """Ghi một sự kiện XP thưởng (không bị trần). True nếu là lần đầu (khóa chống trùng)."""
    return await store.xp.insert_if_absent(NewXpEvent(user_id, source, ref, amount, False, day, now))


async def quest_progress(store: GamificationStore, user_id: int, day: date) -> dict[str, int]:
    counters = await store.activity.day_counters(user_id, day)
    # Nhiệm vụ làm bài tính cả sự kiện XP bị trần, nên đếm sự kiện nguồn `quiz` (F16.04).
    quizzes = await store.xp.count_for_day(user_id, day, XpSource.QUIZ)
    return {"read_pages": counters.pages_read, "review_cards": counters.reviews_count, "take_quiz": quizzes}


async def evaluate_quests(
    store: GamificationStore, user_id: int, trigger: LearningSource, day: date, now: datetime
) -> None:
    """Thưởng ngay nhiệm vụ vừa đạt mục tiêu; đủ cả ba thì cộng xu (khóa `quests_all:<ngày>`)."""
    relevant = [q for q in QUESTS if q.trigger is trigger]
    if not relevant:
        return
    progress = await quest_progress(store, user_id, day)
    newly = False
    for quest in relevant:
        if progress[quest.code] >= quest.target:
            granted = await award_xp(
                store, user_id, XpSource.QUEST, quest_ref(quest.code, day), quest.xp, day, now
            )
            newly = newly or granted
    if not newly:
        return
    refs = [quest_ref(q.code, day) for q in QUESTS]
    if len(await store.xp.rewarded_at(user_id, XpSource.QUEST, refs)) == len(QUESTS):
        await store.rewards.grant(
            user_id,
            RewardBundle(coins=QUEST_ALL_BONUS_COINS),
            quests_all_key(day),
            LedgerReason.QUEST_BONUS,
            now,
        )


async def quests_today(store: GamificationStore, user_id: int, day: date) -> QuestsToday:
    progress = await quest_progress(store, user_id, day)
    refs = [quest_ref(q.code, day) for q in QUESTS]
    rewarded = await store.xp.rewarded_at(user_id, XpSource.QUEST, refs)
    views = [
        QuestView(
            q.code,
            q.name,
            min(progress[q.code], q.target),
            q.target,
            q.xp,
            progress[q.code] >= q.target,
            rewarded.get(quest_ref(q.code, day)),
        )
        for q in QUESTS
    ]
    # Xu thưởng được ghi cùng giao dịch với nhiệm vụ cuối cùng, nên đủ ba lần thưởng nghĩa là đã cộng xu.
    return QuestsToday(day, views, QUEST_ALL_BONUS_COINS, len(rewarded) == len(QUESTS))
