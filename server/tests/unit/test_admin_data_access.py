"""F13.07 (US-QT-14) — quản trị viên xem/sửa dữ liệu người khác; người dùng thường vẫn bị chặn."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from app.core.errors import PermissionDeniedError
from app.modules.admin.application.use_cases.ensure_target_user import EnsureTargetUserUseCase
from app.modules.admin.domain.errors import UserNotFoundError
from app.modules.auth.domain.entities import Role, User, UserStatus
from app.modules.review.application.dto import ListCardsQuery
from app.modules.review.application.use_cases.list_cards import InvalidCardStateError, ListCardsUseCase
from app.modules.review.application.use_cases.reset_card import ResetCardUseCase
from app.modules.review.application.use_cases.suspend_card import SuspendCardUseCase
from app.modules.review.domain.errors import CardNotFoundError
from app.modules.review.infrastructure.fsrs_scheduler import FsrsScheduler
from app.modules.vocab.application.use_cases.delete_context import DeleteContextUseCase
from app.modules.vocab.application.use_cases.delete_vocab import DeleteVocabUseCase
from app.modules.vocab.application.use_cases.get_vocab import GetVocabUseCase
from app.modules.vocab.domain.errors import VocabNotFoundError
from tests.conftest import FixedClock
from tests.unit.review_fakes import admin_identity, identity
from tests.unit.test_review_use_cases import NOW, _uow_with_cards
from tests.unit.test_vocab_use_cases import Env, _saved, _update

OWNER = 1
ADMIN = admin_identity(99)


async def test_admin_updates_other_users_entry_and_it_is_audited() -> None:
    """F13.07, F13.06: sửa từ của người khác thành công và để lại nhật ký, không chứa nội dung ghi chú."""
    env = Env()
    entry = await _saved(env)
    detail = await _update(env).execute(ADMIN, entry.id, {"note": "bí mật", "is_starred": True}, OWNER)
    assert detail.entry.note == "bí mật" and detail.entry.user_id == OWNER
    row = env.uow.audit.rows[-1]
    assert row["action"] == "vocab.update" and row["admin_id"] == 99 and row["id"] == entry.id
    assert row["target_user_id"] == OWNER and row["fields"] == ["is_starred", "note"]
    assert "bí mật" not in str(row)


async def test_admin_reads_and_deletes_other_users_vocab_with_audit() -> None:
    env = Env()
    entry = await _saved(env)
    seen = await GetVocabUseCase(lambda: env.uow, env.pages, env.dictionary, env.clock).execute(
        ADMIN, entry.id, OWNER
    )
    assert seen.entry.id == entry.id and env.uow.audit.rows == []  # xem không bắt buộc ghi
    context_id = next(iter(env.uow.contexts.items))
    await DeleteContextUseCase(lambda: env.uow, env.storage, env.clock).execute(
        ADMIN, entry.id, context_id, OWNER
    )
    await DeleteVocabUseCase(lambda: env.uow, env.storage, env.clock).execute(ADMIN, entry.id, OWNER)
    assert [r["action"] for r in env.uow.audit.rows] == ["vocab.context_delete", "vocab.delete"]
    assert env.uow.entries.items == {}


async def test_owner_editing_own_entry_writes_no_audit() -> None:
    env = Env()
    entry = await _saved(env)
    await _update(env).execute(identity(), entry.id, {"note": "x"})
    await _update(env).execute(ADMIN, entry.id, {"note": "y"}, OWNER)
    assert len(env.uow.audit.rows) == 1


async def test_regular_user_cannot_target_another_user_and_normal_access_stays_404() -> None:
    env = Env()
    entry = await _saved(env)
    with pytest.raises(PermissionDeniedError):
        await _update(env).execute(identity(2), entry.id, {"note": "x"}, OWNER)
    with pytest.raises(VocabNotFoundError):  # đường thường: không chỉ định đích
        await _update(env).execute(identity(2), entry.id, {"note": "x"})
    assert env.uow.audit.rows == []


async def test_admin_manages_other_users_cards_with_audit_and_regular_user_cannot() -> None:
    uow = await _uow_with_cards(user_id=OWNER)
    clock = FixedClock(NOW)
    card_id = next(iter(uow.cards.items))
    await SuspendCardUseCase(lambda: uow, clock).execute(ADMIN, card_id, OWNER)
    assert uow.cards.items[card_id].is_suspended
    await ResetCardUseCase(lambda: uow, FsrsScheduler(enable_fuzzing=False), clock).execute(
        ADMIN, card_id, OWNER
    )
    assert [r["action"] for r in uow.audit.rows] == ["card.suspend", "card.reset"]
    assert uow.audit.rows[0]["target_user_id"] == OWNER
    with pytest.raises(CardNotFoundError):  # người dùng khác qua đường thường vẫn 404
        await SuspendCardUseCase(lambda: uow, clock).execute(identity(2), card_id)
    with pytest.raises(PermissionDeniedError):
        await SuspendCardUseCase(lambda: uow, clock).execute(identity(2), card_id, OWNER)


async def test_list_cards_filters_and_attaches_term() -> None:
    uow = await _uow_with_cards(user_id=OWNER)
    first = next(iter(uow.cards.items.values()))
    first.is_suspended = True
    use_case = ListCardsUseCase(lambda: uow, FixedClock(NOW))
    page = await use_case.execute(ADMIN, ListCardsQuery(suspended=True), OWNER)
    assert page.total == 1 and page.items[0].face is not None and page.items[0].face.term == "你好"
    due = await use_case.execute(ADMIN, ListCardsQuery(due=True, size=1), OWNER)
    assert due.total == 2 and len(due.items) == 1
    with pytest.raises(InvalidCardStateError):
        await use_case.execute(ADMIN, ListCardsQuery(state="khác"), OWNER)
    with pytest.raises(PermissionDeniedError):
        await use_case.execute(identity(2), ListCardsQuery(), OWNER)


class _Users:
    async def get(self, user_id: int) -> User | None:
        if user_id != 5:
            return None
        return User(
            5, "a@b.c", "x", "A", Role.USER, UserStatus.ACTIVE, datetime(2026, 1, 1, tzinfo=timezone.utc)
        )


class _AdminUow:
    users = _Users()

    async def __aenter__(self) -> _AdminUow:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None


async def test_ensure_target_user_checks_role_then_existence() -> None:
    use_case = EnsureTargetUserUseCase(lambda: _AdminUow())  # type: ignore[arg-type, return-value]
    assert (await use_case.execute(ADMIN, 5)).id == 5
    with pytest.raises(UserNotFoundError):
        await use_case.execute(ADMIN, 404)
    with pytest.raises(PermissionDeniedError):
        await use_case.execute(identity(2), 5)
