"""Repository giả của M08 dùng chung cho test đơn vị của M07/M08 (không cần CSDL)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import asdict, replace
from datetime import datetime
from typing import Any

from app.modules.auth.application.public import Identity, Role
from app.modules.review.application.dto import ContextFace, EntryFace
from app.modules.review.domain.entities import (
    Card,
    CardFilter,
    DeckRef,
    EntrySrsSummary,
    NewCard,
    NewReviewLog,
    ReviewLog,
)
from app.modules.review.domain.errors import PresentationIdTakenError
from tests.unit.activity_fakes import FakeActivity, FakeFsrsProfiles


def identity(user_id: int = 1) -> Identity:
    return Identity(user_id=user_id, role=Role.USER, session_id="s")


def admin_identity(user_id: int = 99) -> Identity:
    return Identity(user_id=user_id, role=Role.ADMIN, session_id="s")


class FakeAudit:
    """Nhật ký quản trị giả (F13.06): giữ lại các lần ghi để test kiểm tra."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    async def add(
        self,
        admin_id: int,
        action: str,
        target_type: str,
        target_id: int | None,
        details: dict[str, Any],
        at: datetime,
    ) -> None:
        self.rows.append(
            {"admin_id": admin_id, "action": action, "type": target_type, "id": target_id, **details}
        )


class FakeCards:
    def __init__(self, learning: set[int] | None = None) -> None:
        self.items: dict[int, Card] = {}
        self.learning = learning  # None: mọi mục từ đều "Đang học"
        self._next = 1

    async def add_many(self, new_cards: Sequence[NewCard]) -> list[Card]:
        created = []
        for n in new_cards:
            card = Card(
                id=self._next,
                user_id=n.user_id,
                vocab_entry_id=n.vocab_entry_id,
                card_type=n.card_type,
                schedule=n.schedule,
                reps=0,
                lapses=0,
                is_suspended=False,
                created_at=n.created_at,
                updated_at=n.created_at,
            )
            self._next += 1
            self.items[card.id] = card
            created.append(card)
        return created

    async def get(self, user_id: int, card_id: int) -> Card | None:
        card = self.items.get(card_id)
        return card if card and card.user_id == user_id else None

    async def get_for_update(self, user_id: int, card_id: int) -> Card | None:
        return await self.get(user_id, card_id)

    async def save(self, card: Card) -> None:
        self.items[card.id] = card

    def _eligible(
        self, user_id: int, as_of: datetime, entry_ids: Sequence[int] | None, exclude: int | None
    ) -> list[Card]:
        cards = [
            c
            for c in self.items.values()
            if c.user_id == user_id
            and not c.is_suspended
            and c.schedule.due_at <= as_of
            and (self.learning is None or c.vocab_entry_id in self.learning)
            and (entry_ids is None or c.vocab_entry_id in entry_ids)
            and c.id != exclude
        ]
        return sorted(cards, key=lambda c: (c.schedule.due_at, c.id))

    async def list_due(
        self,
        user_id: int,
        now: datetime,
        limit: int,
        entry_ids: Sequence[int] | None,
        exclude_card_id: int | None,
    ) -> list[Card]:
        return self._eligible(user_id, now, entry_ids, exclude_card_id)[:limit]

    async def count_due(
        self, user_id: int, as_of: datetime, entry_ids: Sequence[int] | None, exclude_card_id: int | None
    ) -> int:
        return len(self._eligible(user_id, as_of, entry_ids, exclude_card_id))

    async def count_due_words(self, user_id: int, as_of: datetime) -> int:
        return len({c.vocab_entry_id for c in self._eligible(user_id, as_of, None, None)})

    async def next_due_after(self, user_id: int, now: datetime) -> datetime | None:
        later = [
            c.schedule.due_at
            for c in self.items.values()
            if c.user_id == user_id and not c.is_suspended and c.schedule.due_at > now
        ]
        return min(later) if later else None

    async def count_cards(self, user_id: int) -> int:
        return sum(1 for c in self.items.values() if c.user_id == user_id)

    async def list_for_entry(self, user_id: int, vocab_entry_id: int) -> list[Card]:
        return [c for c in self.items.values() if c.user_id == user_id and c.vocab_entry_id == vocab_entry_id]

    async def list_for_entries(self, user_id: int, vocab_entry_ids: Sequence[int]) -> list[Card]:
        return [
            c for c in self.items.values() if c.user_id == user_id and c.vocab_entry_id in vocab_entry_ids
        ]

    async def bury_siblings(
        self, user_id: int, vocab_entry_id: int, graded_card_id: int, now: datetime, until: datetime
    ) -> int:
        moved = 0
        for card in self.items.values():
            same_entry = card.user_id == user_id and card.vocab_entry_id == vocab_entry_id
            if (
                same_entry
                and card.id != graded_card_id
                and not card.is_suspended
                and card.schedule.due_at <= now
            ):
                card.schedule = replace(card.schedule, due_at=until)
                card.updated_at = now
                moved += 1
        return moved

    async def reschedule_now(self, user_id: int, vocab_entry_ids: Sequence[int], now: datetime) -> int:
        cards = await self.list_for_entries(user_id, vocab_entry_ids)
        for card in cards:
            card.schedule = replace(card.schedule, due_at=now)
            card.is_suspended = False
            card.updated_at = now
        return len(cards)

    async def search(self, flt: CardFilter, offset: int, limit: int) -> tuple[list[Card], int]:
        rows = [
            c
            for c in self.items.values()
            if c.user_id == flt.user_id
            and (flt.state is None or c.schedule.state is flt.state)
            and (flt.suspended is None or c.is_suspended is flt.suspended)
        ]
        if flt.due is not None:
            due_ids = {c.id for c in self._eligible(flt.user_id, flt.now, None, None)}
            rows = [c for c in rows if (c.id in due_ids) is flt.due]
        rows.sort(key=lambda c: (c.schedule.due_at, c.id))
        return rows[offset : offset + limit], len(rows)

    async def summaries_for_entries(
        self, user_id: int, entry_ids: Sequence[int], now: datetime
    ) -> dict[int, EntrySrsSummary]:
        result: dict[int, EntrySrsSummary] = {}
        for entry_id in entry_ids:
            cards = await self.list_for_entry(user_id, entry_id)
            if cards:
                due = sum(1 for c in cards if not c.is_suspended and c.schedule.due_at <= now)
                result[entry_id] = EntrySrsSummary(
                    entry_id,
                    len(cards),
                    due,
                    sum(c.reps for c in cards),
                    min(c.schedule.due_at for c in cards),
                )
        return result


class FakeLogs:
    def __init__(self) -> None:
        self.items: list[ReviewLog] = []

    async def add(self, new_log: NewReviewLog) -> ReviewLog:
        if any(i.presentation_id == new_log.presentation_id for i in self.items):
            raise PresentationIdTakenError()
        log = ReviewLog(id=len(self.items) + 1, **asdict(new_log))
        self.items.append(log)
        return log

    async def find_by_presentation(self, presentation_id: uuid.UUID) -> ReviewLog | None:
        return next((i for i in self.items if i.presentation_id == presentation_id), None)

    async def list_for_card(self, card_id: int, offset: int, limit: int) -> tuple[list[ReviewLog], int]:
        rows = sorted(
            (i for i in self.items if i.card_id == card_id), key=lambda i: i.reviewed_at, reverse=True
        )
        return rows[offset : offset + limit], len(rows)

    async def count_between(self, user_id: int, start: datetime, end: datetime) -> int:
        return sum(1 for i in self.items if i.user_id == user_id and start <= i.reviewed_at < end)

    async def count_for_user(self, user_id: int) -> int:
        return sum(1 for i in self.items if i.user_id == user_id)


class FakeVocabSource:
    def __init__(self) -> None:
        self.faces_by_id: dict[int, EntryFace] = {}
        self.decks: dict[str, list[int]] = {}

    def add_face(self, entry_id: int, term: str = "你好", status: str = "learning") -> None:
        self.faces_by_id[entry_id] = EntryFace(
            vocab_entry_id=entry_id,
            term=term,
            pinyin="nǐ hǎo",
            meaning_vi="xin chào",
            sino_vietnamese="nhĩ hảo",
            note="mẹo nhớ",
            status=status,
            is_starred=False,
            hsk_level=1,
            context=ContextFace(1, 10, "你好吗", "Bạn khỏe không", "Truyện · Chương 1 · Trang 1"),
            contexts_count=1,
        )

    async def faces(self, user_id: int, entry_ids: Sequence[int]) -> dict[int, EntryFace]:
        return {i: self.faces_by_id[i] for i in entry_ids if i in self.faces_by_id}

    async def status_counts(self, user_id: int) -> dict[str, int]:
        counts = {"learning": 0, "known": 0, "ignored": 0}
        for face in self.faces_by_id.values():
            counts[face.status] += 1
        return counts

    async def entry_ids_for_deck(self, user_id: int, deck: DeckRef) -> list[int]:
        return list(self.decks.get(deck.key, []))


class FakeReviewUow:
    def __init__(self, cards: FakeCards | None = None, logs: FakeLogs | None = None) -> None:
        self.cards = cards or FakeCards()
        self.logs = logs or FakeLogs()
        self.vocab = FakeVocabSource()
        self.audit = FakeAudit()
        self.activity = FakeActivity()
        self.fsrs_profiles = FakeFsrsProfiles()
        self.commits = 0

    async def __aenter__(self) -> FakeReviewUow:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1
