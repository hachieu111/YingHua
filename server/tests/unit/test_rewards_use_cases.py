"""M17 - use case với repository giả: ghi sổ idempotent, số dư không âm, đổi thưởng, mở khóa, khung."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from app.core.errors import PermissionDeniedError
from app.modules.rewards.application.ai_policy import VipAwareAiPolicy
from app.modules.rewards.application.dto import (
    CreateItemCommand,
    GrantCommand,
    RedeemCommand,
    VipGrantCommand,
    WalletAdjustCommand,
)
from app.modules.rewards.application.use_cases.adjust_wallet import AdjustWalletUseCase
from app.modules.rewards.application.use_cases.create_reward_item import CreateRewardItemUseCase
from app.modules.rewards.application.use_cases.equip_frame import EquipFrameUseCase
from app.modules.rewards.application.use_cases.get_user_rewards import GetUserRewardsUseCase
from app.modules.rewards.application.use_cases.get_wallet import GetWalletUseCase
from app.modules.rewards.application.use_cases.grant_reward import GrantRewardUseCase
from app.modules.rewards.application.use_cases.grant_vip import GrantVipUseCase
from app.modules.rewards.application.use_cases.grant_welcome_gift import GrantWelcomeGiftUseCase
from app.modules.rewards.application.use_cases.list_frames import ListFramesUseCase
from app.modules.rewards.application.use_cases.list_shop_items import ListShopItemsUseCase
from app.modules.rewards.application.use_cases.redeem_item import RedeemItemUseCase
from app.modules.rewards.application.use_cases.remind_vip_expiry import RemindVipExpiryUseCase
from app.modules.rewards.application.use_cases.set_series_vip import SetSeriesVipUseCase
from app.modules.rewards.application.use_cases.unlock_series import UnlockSeriesUseCase
from app.modules.rewards.application.use_cases.update_reward_item import UpdateRewardItemUseCase
from app.modules.rewards.domain.entities import (
    Currency,
    FrameGrant,
    FrameSource,
    LedgerReason,
    RewardBundle,
)
from app.modules.rewards.domain.errors import (
    FrameAlreadyOwnedError,
    FrameNotAvailableError,
    InvalidRewardError,
    NotEnoughCoinsError,
    NotEnoughTicketsError,
    RequestReusedError,
    RewardItemCodeTakenError,
    RewardItemLockedError,
    RewardItemUnavailableError,
    RewardLimitReachedError,
    SeriesAlreadyUnlockedError,
    SeriesNotPublicError,
    SeriesNotVipError,
    TicketLimitReachedError,
    VipNotActiveError,
    VipSeriesNotFoundError,
    WalletNegativeError,
)
from tests.conftest import FixedClock
from tests.unit.review_fakes import admin_identity, identity
from tests.unit.rewards_fakes import NOW, FakeNotifier, FakeRewardsUow

ME = identity(1)
ADMIN = admin_identity(99)


class Env:
    def __init__(self) -> None:
        self.uow = FakeRewardsUow()
        self.clock = FixedClock(NOW)
        self.notifier = FakeNotifier()

    def factory(self):  # type: ignore[no-untyped-def]
        return lambda: self.uow

    def grant(self) -> GrantRewardUseCase:
        return GrantRewardUseCase(self.factory(), self.clock)

    async def give(self, *, coins: int = 0, tickets: int = 0, days: int = 0, key: str = "k") -> None:
        bundle = RewardBundle(coins=coins, tickets=tickets, vip_days=days)
        await self.grant().execute(GrantCommand(1, bundle, key, LedgerReason.QUEST_BONUS))

    async def wallet(self, user_id: int = 1):  # type: ignore[no-untyped-def]
        return await GetWalletUseCase(self.factory(), self.clock).execute(identity(user_id))


@pytest.fixture
def env() -> Env:
    return Env()


# ---- F17.01 ghi sổ -------------------------------------------------------------------------------


async def test_grant_is_idempotent_per_key_and_returns_current_balance(env: Env) -> None:
    """F17.01: gọi lại cùng khóa không cộng hai lần, không phải lỗi."""
    first = await env.grant().execute(
        GrantCommand(1, RewardBundle(coins=20), "quests_all:2026-10-30", LedgerReason.QUEST_BONUS)
    )
    again = await env.grant().execute(
        GrantCommand(1, RewardBundle(coins=20), "quests_all:2026-10-30", LedgerReason.QUEST_BONUS)
    )
    assert (first.duplicate, again.duplicate) == (False, True)
    assert again.wallet.coin_balance == 20 and len(env.uow.wallets.ledger) == 1
    other_day = await env.grant().execute(
        GrantCommand(1, RewardBundle(coins=20), "quests_all:2026-10-31", LedgerReason.QUEST_BONUS)
    )
    assert other_day.wallet.coin_balance == 40


async def test_one_key_covers_each_currency_separately(env: Env) -> None:
    """Gói nhiều loại dùng chung khóa: mỗi loại ghi một dòng sổ; loại đã có thì bỏ qua riêng loại đó."""
    await env.grant().execute(GrantCommand(1, RewardBundle(coins=50), "season:7", LedgerReason.SEASON_REWARD))
    result = await env.grant().execute(
        GrantCommand(1, RewardBundle(coins=50, tickets=3), "season:7", LedgerReason.SEASON_REWARD)
    )
    assert result.duplicate is False
    assert (result.wallet.coin_balance, result.wallet.ticket_balance) == (50, 3)
    assert sorted(e.currency.value for e in env.uow.wallets.ledger) == ["coin", "ticket"]


async def test_coins_and_tickets_never_go_negative(env: Env) -> None:
    """US-NH-93 TC4: khoản trừ vượt số dư bị từ chối, không ghi gì."""
    await env.give(coins=100, tickets=1)
    with pytest.raises(NotEnoughCoinsError) as coin_error:
        await env.grant().execute(GrantCommand(1, RewardBundle(coins=-101), "x", LedgerReason.REDEMPTION))
    assert coin_error.value.details == {"required": 101, "balance": 100, "missing": 1}
    with pytest.raises(NotEnoughTicketsError):
        await env.grant().execute(GrantCommand(1, RewardBundle(tickets=-2), "y", LedgerReason.VIP_UNLOCK))
    wallet = await env.wallet()
    assert (wallet.coin_balance, wallet.ticket_balance) == (100, 1)
    assert len(env.uow.wallets.ledger) == 2


async def test_grant_requires_reason_when_bundle_has_currency(env: Env) -> None:
    with pytest.raises(InvalidRewardError):
        await env.grant().execute(GrantCommand(1, RewardBundle(coins=5), "k"))


async def test_system_ticket_grant_clamps_at_wallet_cap_but_redemption_is_rejected(env: Env) -> None:
    """Ví chứa tối đa 99 vé: thưởng tự động bị cắt về trần, đổi thưởng/điều chỉnh bị từ chối."""
    await env.give(tickets=10, key="a")
    for i in range(8):
        await env.give(tickets=10, key=f"b{i}")
    assert (await env.wallet()).ticket_balance == 90
    await env.grant().execute(GrantCommand(1, RewardBundle(tickets=10), "c", LedgerReason.SEASON_REWARD))
    assert (await env.wallet()).ticket_balance == 99
    last = next(e for e in env.uow.wallets.ledger if e.idempotency_key == "c")
    assert last.amount == 9 and last.balance_after == 99
    with pytest.raises(TicketLimitReachedError):
        await env.grant().execute(GrantCommand(1, RewardBundle(tickets=1), "d", LedgerReason.ADMIN_ADJUST))


async def test_vip_days_stack_and_ledger_records_new_expiry(env: Env) -> None:
    """F17.03: cộng dồn; dòng sổ ghi hạn VIP sau."""
    await env.give(days=2, key="a")
    await env.give(days=7, key="b")
    wallet = await env.wallet()
    assert wallet.vip.is_active and wallet.vip.vip_until == NOW + timedelta(days=9)
    assert env.uow.wallets.ledger[-1].vip_until_after == NOW + timedelta(days=9)


async def test_frame_grant_extends_temporary_frame_and_never_downgrades_permanent(env: Env) -> None:
    """F16.05/F17.08: khung 7 ngày nhận lại thì gia hạn; đã vĩnh viễn thì giữ nguyên."""
    weekly = RewardBundle(frame=FrameGrant("sakura_gold", FrameSource.WEEKLY_GOAL, days=7))
    first = await env.grant().execute(GrantCommand(1, weekly, "w1"))
    assert first.frame is not None and first.frame.expires_at == NOW + timedelta(days=7)
    env.clock.at = NOW + timedelta(days=3)
    second = await env.grant().execute(GrantCommand(1, weekly, "w2"))
    assert second.frame is not None and second.frame.expires_at == NOW + timedelta(days=10)
    forever = RewardBundle(frame=FrameGrant("sakura_gold", FrameSource.SEASON))
    permanent = await env.grant().execute(GrantCommand(1, forever, "s1"))
    assert permanent.frame is not None and permanent.frame.expires_at is None
    again = await env.grant().execute(GrantCommand(1, weekly, "w3"))
    assert again.frame is not None and again.frame.expires_at is None


async def test_unknown_frame_is_rejected(env: Env) -> None:
    with pytest.raises(InvalidRewardError):
        await env.grant().execute(
            GrantCommand(1, RewardBundle(frame=FrameGrant("khong_co", FrameSource.ADMIN)), "k")
        )


# ---- F17.03 quà chào mừng và nhắc hết hạn -------------------------------------------------------


async def test_welcome_gift_grants_three_days_once_and_notifies(env: Env) -> None:
    """US-NH-94 TC1: 3 ngày VIP, đúng một lần mỗi tài khoản, kèm thông báo."""
    gift = GrantWelcomeGiftUseCase(env.factory(), env.clock, env.notifier)
    await gift.grant_welcome(1)
    await gift.grant_welcome(1)
    wallet = await env.wallet()
    assert wallet.vip.is_active and wallet.vip.days_left == 3
    assert env.notifier.events == [("vip_granted", 1)]
    assert len([e for e in env.uow.wallets.ledger if e.reason is LedgerReason.WELCOME]) == 1


async def test_vip_expires_by_time_without_any_job(env: Env) -> None:
    """US-NH-94 TC3: hạn đã qua thì yêu cầu kế tiếp được xử lý như không VIP."""
    await env.give(days=1)
    assert (await env.wallet()).vip.is_active
    env.clock.at = NOW + timedelta(days=1, seconds=1)
    after = await env.wallet()
    assert not after.vip.is_active and after.vip.days_left == 0


async def test_reminder_sends_once_per_expiry_and_again_after_extension(env: Env) -> None:
    """US-HG-06: đúng một thông báo cho mỗi hạn; cộng thêm ngày thì nhắc lại cho hạn mới."""
    await env.give(days=1, key="a")
    remind = RemindVipExpiryUseCase(env.factory(), env.notifier)
    later = NOW + timedelta(hours=6)  # còn 18 giờ
    first = await remind.execute(later)
    second = await remind.execute(later)
    assert (first.reminded, second.reminded, second.scanned) == (1, 0, 0)
    await env.give(days=1, key="b")  # hạn mới = NOW + 2 ngày, còn 42 giờ: chưa trong 24 giờ
    assert (await remind.execute(later)).scanned == 0
    much_later = NOW + timedelta(days=1, hours=12)  # còn 12 giờ cho hạn mới
    assert (await remind.execute(much_later)).reminded == 1
    assert [e[0] for e in env.notifier.events] == ["vip_expiring", "vip_expiring"]


async def test_reminder_failure_is_logged_and_retried_next_run(env: Env) -> None:
    """US-HG-06 TC5: gửi lỗi thì không ghi "đã nhắc", lần chạy sau thử lại."""
    await env.give(days=1)
    remind = RemindVipExpiryUseCase(env.factory(), env.notifier)
    env.notifier.fail = True
    later = NOW + timedelta(hours=6)
    failed = await remind.execute(later)
    assert (failed.failed, failed.reminded) == (1, 0)
    env.notifier.fail = False
    assert (await remind.execute(later)).reminded == 1


async def test_reminder_skips_expired_and_far_expiry(env: Env) -> None:
    await env.give(days=10)
    remind = RemindVipExpiryUseCase(env.factory(), env.notifier)
    assert (await remind.execute(NOW)).scanned == 0
    assert (await remind.execute(NOW + timedelta(days=11))).scanned == 0


# ---- F17.04 hạn mức AI ----------------------------------------------------------------------------


class _Vip:
    def __init__(self, vip: bool, fail: bool = False) -> None:
        self.vip, self.fail = vip, fail

    async def is_vip(self, user_id: int, now: datetime) -> bool:
        if self.fail:
            raise RuntimeError("CSDL lỗi")
        return self.vip


class _Base:
    async def llm_enabled(self) -> bool:
        return False

    async def daily_limit(self, user_id: int) -> int:
        return 5


class _Snapshot:
    def __init__(self, vip_limit: int) -> None:
        self.vip_quiz_daily_llm_limit = vip_limit


class _Settings:
    def __init__(self, vip_limit: int) -> None:
        self._vip_limit = vip_limit

    async def snapshot(self) -> _Snapshot:
        return _Snapshot(self._vip_limit)


def _policy(vip: _Vip, vip_limit: int = 10) -> VipAwareAiPolicy:
    return VipAwareAiPolicy(
        _Base(),
        _Settings(vip_limit),  # type: ignore[arg-type]
        lambda s: s.vip_quiz_daily_llm_limit,
        vip,
        FixedClock(NOW),
    )


async def test_vip_ai_policy_raises_limit_only_while_vip_and_keeps_llm_switch() -> None:
    """US-NH-95 TC1, TC3, TC5: VIP 10 (thường 5); VIP thấp hơn thì dùng thường; tắt LLM cho mọi người."""
    assert await _policy(_Vip(True)).daily_limit(1) == 10
    assert await _policy(_Vip(False)).daily_limit(1) == 5
    assert await _policy(_Vip(True), vip_limit=3).daily_limit(1) == 5
    assert await _policy(_Vip(True)).llm_enabled() is False


async def test_vip_ai_policy_falls_back_to_normal_limit_when_status_unreadable() -> None:
    """F17.04: không đọc được trạng thái VIP thì dùng hạn mức thường, không chặn tính năng."""
    assert await _policy(_Vip(True, fail=True)).daily_limit(1) == 5


# ---- F17.06 mở khóa truyện VIP --------------------------------------------------------------------


async def test_unlock_series_spends_one_ticket_and_replay_does_not_charge_again(env: Env) -> None:
    """US-NH-97 TC1, TC2."""
    env.uow.series.add(12, vip=True)
    await env.give(tickets=2)
    unlock = UnlockSeriesUseCase(env.factory(), env.clock)
    request_id = uuid.uuid4()
    first = await unlock.execute(ME, 12, request_id)
    replay = await unlock.execute(ME, 12, request_id)
    assert (first.tickets_left, replay.tickets_left) == (1, 1)
    assert replay.unlock.series_id == 12
    assert (await env.wallet()).ticket_balance == 1


async def test_unlock_rejections_do_not_spend_tickets(env: Env) -> None:
    """US-NH-97 TC3, TC4: hết vé, không phải truyện VIP, đã mở khóa, truyện không thấy được."""
    env.uow.series.add(12, vip=True)
    env.uow.series.add(13, vip=False)
    env.uow.series.add(14, vip=True, public=False, owner_id=77)
    unlock = UnlockSeriesUseCase(env.factory(), env.clock)
    with pytest.raises(NotEnoughTicketsError):
        await unlock.execute(ME, 12, uuid.uuid4())
    await env.give(tickets=3)
    with pytest.raises(SeriesNotVipError):
        await unlock.execute(ME, 13, uuid.uuid4())
    with pytest.raises(VipSeriesNotFoundError):
        await unlock.execute(ME, 999, uuid.uuid4())
    with pytest.raises(VipSeriesNotFoundError):
        await unlock.execute(ME, 14, uuid.uuid4())
    await unlock.execute(ME, 12, uuid.uuid4())
    with pytest.raises(SeriesAlreadyUnlockedError):
        await unlock.execute(ME, 12, uuid.uuid4())
    assert (await env.wallet()).ticket_balance == 2


async def test_unlock_request_id_cannot_be_reused_for_another_series(env: Env) -> None:
    env.uow.series.add(12, vip=True)
    env.uow.series.add(13, vip=True)
    await env.give(tickets=2)
    unlock = UnlockSeriesUseCase(env.factory(), env.clock)
    request_id = uuid.uuid4()
    await unlock.execute(ME, 12, request_id)
    with pytest.raises(RequestReusedError):
        await unlock.execute(ME, 13, request_id)


# ---- F17.07 cửa hàng -------------------------------------------------------------------------------


async def test_redeem_vip_days_spends_coins_and_stacks_vip(env: Env) -> None:
    """US-NH-98 TC2: 800 xu đổi 7 ngày VIP (700) còn 100, hạn VIP cộng dồn, có dòng sổ tiêu xu."""
    await env.give(coins=800, days=2)
    redeem = RedeemItemUseCase(env.factory(), env.clock)
    result = await redeem.execute(ME, RedeemCommand(2, uuid.uuid4()))
    assert result.wallet.coin_balance == 100
    assert result.wallet.vip.vip_until == NOW + timedelta(days=9)
    assert result.redemption.price_coins == 700
    spent = [
        e
        for e in env.uow.wallets.ledger
        if e.reason is LedgerReason.REDEMPTION and e.currency is Currency.COIN
    ]
    assert [(e.amount, e.balance_after) for e in spent] == [(-700, 100)]


async def test_redeem_replay_with_same_request_id_charges_once(env: Env) -> None:
    """US-NH-98 TC4."""
    await env.give(coins=1000)
    redeem = RedeemItemUseCase(env.factory(), env.clock)
    request_id = uuid.uuid4()
    first = await redeem.execute(ME, RedeemCommand(1, request_id))
    second = await redeem.execute(ME, RedeemCommand(1, request_id))
    assert first.redemption.id == second.redemption.id
    assert (await env.wallet()).coin_balance == 880 and len(env.uow.shop.redemptions) == 1


async def test_redeem_not_enough_coins_reports_missing_and_keeps_balance(env: Env) -> None:
    """US-NH-98 TC3."""
    await env.give(coins=100)
    redeem = RedeemItemUseCase(env.factory(), env.clock)
    with pytest.raises(NotEnoughCoinsError) as error:
        await redeem.execute(ME, RedeemCommand(1, uuid.uuid4()))
    assert error.value.details["missing"] == 20
    assert (await env.wallet()).coin_balance == 100 and not env.uow.shop.redemptions


async def test_redeem_frame_cannot_be_bought_twice_and_respects_per_user_limit(env: Env) -> None:
    """US-NH-98 TC5: đã sở hữu khung thì bị từ chối, không trừ xu; vượt giới hạn mỗi người cũng vậy."""
    await env.give(coins=3000)
    redeem = RedeemItemUseCase(env.factory(), env.clock)
    await redeem.execute(ME, RedeemCommand(4, uuid.uuid4()))
    with pytest.raises(FrameAlreadyOwnedError):
        await redeem.execute(ME, RedeemCommand(4, uuid.uuid4()))
    await redeem.execute(ME, RedeemCommand(5, uuid.uuid4()))
    env.uow.shop.items[5].per_user_limit = 1
    env.uow.wallets.user_frames.clear()  # bỏ sở hữu khung để chỉ còn giới hạn lượt đổi chặn
    with pytest.raises(RewardLimitReachedError):
        await redeem.execute(ME, RedeemCommand(5, uuid.uuid4()))
    assert (await env.wallet()).coin_balance == 3000 - 1600


async def test_redeem_unavailable_item_and_ticket_cap(env: Env) -> None:
    await env.give(coins=1000)
    redeem = RedeemItemUseCase(env.factory(), env.clock)
    with pytest.raises(RewardItemUnavailableError):
        await redeem.execute(ME, RedeemCommand(999, uuid.uuid4()))
    env.uow.shop.items[1].is_active = False
    with pytest.raises(RewardItemUnavailableError):
        await redeem.execute(ME, RedeemCommand(1, uuid.uuid4()))
    for i in range(9):
        await env.give(tickets=10, key=f"t{i}")
    await env.give(tickets=9, key="top")
    with pytest.raises(TicketLimitReachedError):
        await redeem.execute(ME, RedeemCommand(3, uuid.uuid4()))
    assert (await env.wallet()).coin_balance == 1000  # đã hoàn tác cả khoản trừ xu


async def test_shop_list_flags_affordable_owned_and_remaining(env: Env) -> None:
    """US-NH-98 TC1: món đang bán kèm giá, đủ xu, khung đã sở hữu, lượt còn lại."""
    await env.give(coins=800)
    redeem = RedeemItemUseCase(env.factory(), env.clock)
    await redeem.execute(ME, RedeemCommand(5, uuid.uuid4()))
    views = {v.item.code: v for v in await ListShopItemsUseCase(env.factory()).execute(ME)}
    assert set(views) == {"vip_1d", "vip_7d", "vip_ticket", "frame_bamboo", "frame_ink"}
    assert views["vip_1d"].affordable is False  # còn 0 xu
    assert views["frame_ink"].owned is True and views["frame_ink"].remaining == 0
    assert views["frame_bamboo"].owned is False and views["frame_bamboo"].remaining is None
    env.uow.shop.items[1].is_active = False
    assert "vip_1d" not in {v.item.code for v in await ListShopItemsUseCase(env.factory()).execute(ME)}


# ---- F17.08 khung avatar ---------------------------------------------------------------------------


async def test_equip_frame_rules_for_owned_vip_and_unowned_frames(env: Env) -> None:
    """US-NH-99 TC2-TC5."""
    equip = EquipFrameUseCase(env.factory(), env.clock)
    with pytest.raises(FrameNotAvailableError):
        await equip.execute(ME, "bamboo_leaf")  # chưa sở hữu
    with pytest.raises(FrameNotAvailableError):
        await equip.execute(ME, "vip_sakura")  # khung VIP khi không VIP
    with pytest.raises(FrameNotAvailableError):
        await equip.execute(ME, "khong_co")
    await env.give(days=1)
    frame = await equip.execute(ME, "vip_sakura")
    assert frame is not None and (await env.wallet()).equipped_frame is not None
    env.clock.at = NOW + timedelta(days=2)  # hết VIP: khung VIP tự không hiện
    assert (await env.wallet()).equipped_frame is None
    assert await equip.execute(ME, None) is None


async def test_failed_equip_keeps_current_frame_and_expired_frame_hides_itself(env: Env) -> None:
    await env.grant().execute(
        GrantCommand(1, RewardBundle(frame=FrameGrant("sakura_gold", FrameSource.WEEKLY_GOAL, days=7)), "w")
    )
    equip = EquipFrameUseCase(env.factory(), env.clock)
    await equip.execute(ME, "sakura_gold")
    with pytest.raises(FrameNotAvailableError):
        await equip.execute(ME, "ink_cloud")
    assert (await env.wallet()).equipped_frame.code == "sakura_gold"  # type: ignore[union-attr]
    env.clock.at = NOW + timedelta(days=8)  # US-NH-99 TC3
    assert (await env.wallet()).equipped_frame is None
    views = {v.frame.code: v for v in await ListFramesUseCase(env.factory(), env.clock).execute(ME)}
    assert views["sakura_gold"].owned is False and views["sakura_gold"].equipped is False
    assert views["vip_sakura"].equippable is False


# ---- F17.09 quản trị truyện VIP và danh mục --------------------------------------------------------


async def test_set_series_vip_rules_and_audit(env: Env) -> None:
    """US-QT-17 TC1, TC2, TC6."""
    env.uow.series.add(1)
    env.uow.series.add(2, public=False, owner_id=5)
    use_case = SetSeriesVipUseCase(env.factory(), env.clock)
    with pytest.raises(PermissionDeniedError):
        await use_case.execute(ME, 1, True)
    with pytest.raises(SeriesNotPublicError):
        await use_case.execute(ADMIN, 2, True)
    with pytest.raises(VipSeriesNotFoundError):
        await use_case.execute(ADMIN, 99, True)
    result = await use_case.execute(ADMIN, 1, True)
    assert result.is_vip and result.warning == "Truyện chưa có chương đọc thử"
    env.uow.series.trial.add(1)
    assert (await use_case.execute(ADMIN, 1, True)).warning is None
    await use_case.execute(ADMIN, 1, False)
    assert [c[1] for c in env.uow.audit.calls] == ["series.vip_changed", "series.vip_changed"]


async def test_create_and_update_reward_items_validate_and_audit(env: Env) -> None:
    """US-QT-17 TC3-TC6."""
    create = CreateRewardItemUseCase(env.factory(), env.clock)
    update = UpdateRewardItemUseCase(env.factory(), env.clock)
    new = CreateItemCommand("vip_30d", "30 ngày VIP", "vip_days", 2500, vip_days=30)
    with pytest.raises(PermissionDeniedError):
        await create.execute(ME, new)
    created = await create.execute(ADMIN, new)
    assert created.item.code == "vip_30d" and created.item.price_coins == 2500
    with pytest.raises(RewardItemCodeTakenError):
        await create.execute(ADMIN, CreateItemCommand("vip_30d", "trùng", "vip_days", 10, vip_days=1))
    for bad in (
        CreateItemCommand("gia_cao", "x", "vip_days", 100_001, vip_days=1),
        CreateItemCommand("sai_loai", "x", "vip_ticket", 10, vip_days=1),
        CreateItemCommand("khung_mua", "x", "avatar_frame", 10, frame_code="sakura_gold"),
        CreateItemCommand("khung_vip", "x", "avatar_frame", 10, frame_code="vip_sakura"),
    ):
        with pytest.raises(InvalidRewardError):
            await create.execute(ADMIN, bad)
    changed = await update.execute(ADMIN, created.item.id, {"price_coins": 2000, "is_active": False})
    assert changed.item.price_coins == 2000 and changed.item.is_active is False
    actions = [c[1] for c in env.uow.audit.calls]
    assert actions == ["reward_item.created", "reward_item.updated"]
    assert env.uow.audit.calls[-1][4]["changes"]["price_coins"] == {"from": 2500, "to": 2000}


async def test_item_with_redemptions_cannot_change_target_but_can_stop_selling(env: Env) -> None:
    """US-QT-17 TC4: món đã có lượt đổi chỉ ngừng bán; lịch sử giữ giá cũ."""
    await env.give(coins=500)
    await RedeemItemUseCase(env.factory(), env.clock).execute(ME, RedeemCommand(1, uuid.uuid4()))
    update = UpdateRewardItemUseCase(env.factory(), env.clock)
    with pytest.raises(RewardItemLockedError):
        await update.execute(ADMIN, 1, {"vip_days": 2})
    stopped = await update.execute(ADMIN, 1, {"is_active": False, "price_coins": 999})
    assert stopped.item.is_active is False and stopped.redemption_count_locked is True
    assert env.uow.shop.redemptions[0].price_coins == 120  # giá lúc đổi không đổi
    with pytest.raises(InvalidRewardError):
        await update.execute(ADMIN, 1, {"ticket_count": 2})  # không thuộc loại của món
    with pytest.raises(InvalidRewardError):
        await update.execute(ADMIN, 1, {"kind": "vip_ticket"})


# ---- F17.10 quản trị ví của người dùng ----------------------------------------------------------------


def _admin_cases(env: Env) -> tuple[GrantVipUseCase, AdjustWalletUseCase]:
    return (
        GrantVipUseCase(env.factory(), env.clock, env.notifier),
        AdjustWalletUseCase(env.factory(), env.clock, env.notifier),
    )


async def test_admin_adjust_wallet_rejects_negative_result_and_audits_success(env: Env) -> None:
    """US-QT-18 TC3, TC6."""
    await env.give(coins=100)
    _, adjust = _admin_cases(env)
    with pytest.raises(WalletNegativeError):
        await adjust.execute(ADMIN, WalletAdjustCommand(1, Currency.COIN, -200, "gian lận"))
    assert (await env.wallet()).coin_balance == 100 and not env.uow.audit.calls
    view = await adjust.execute(ADMIN, WalletAdjustCommand(1, Currency.COIN, -40, "thu hồi xu gian lận"))
    assert view.coin_balance == 60
    entry = env.uow.wallets.ledger[-1]
    assert (entry.reason, entry.actor_id, entry.note) == (
        LedgerReason.ADMIN_ADJUST,
        99,
        "thu hồi xu gian lận",
    )
    action, details = env.uow.audit.calls[0][1], env.uow.audit.calls[0][4]
    assert action == "rewards.wallet_adjusted" and details["target_user_id"] == 1 and details["amount"] == -40
    assert env.notifier.events == [("wallet_adjusted", 1)]


async def test_admin_adjust_wallet_validation_and_permission(env: Env) -> None:
    """US-QT-18 TC5: thiếu lý do, số 0, vượt giới hạn; Người học bị từ chối."""
    _, adjust = _admin_cases(env)
    with pytest.raises(PermissionDeniedError):
        await adjust.execute(ME, WalletAdjustCommand(1, Currency.COIN, 5, "x"))
    for command in (
        WalletAdjustCommand(1, Currency.COIN, 5, "   "),
        WalletAdjustCommand(1, Currency.COIN, 0, "x"),
        WalletAdjustCommand(1, Currency.COIN, 100_001, "x"),
        WalletAdjustCommand(1, Currency.TICKET, 11, "x"),
        WalletAdjustCommand(1, Currency.VIP_DAYS, 5, "x"),
    ):
        with pytest.raises(InvalidRewardError):
            await adjust.execute(ADMIN, command)
    assert not env.uow.wallets.ledger and not env.uow.audit.calls


async def test_admin_can_adjust_and_grant_vip_to_self_with_audit(env: Env) -> None:
    """US-QT-18 TC4: tự cấp cho chính mình được phép và vẫn ghi nhật ký (người thực hiện = người nhận)."""
    grant, adjust = _admin_cases(env)
    await adjust.execute(ADMIN, WalletAdjustCommand(99, Currency.TICKET, 3, "tự thử"))
    await grant.execute(ADMIN, VipGrantCommand(99, "tự thử", days=5))
    wallet = await env.wallet(99)
    assert wallet.ticket_balance == 3 and wallet.vip.days_left == 5
    assert [(c[0], c[3]) for c in env.uow.audit.calls] == [(99, 99), (99, 99)]


async def test_admin_grant_stacks_and_revoke_sets_expiry_to_now(env: Env) -> None:
    """US-QT-18 TC2: cấp cộng dồn; thu hồi đưa hạn về hiện tại và ghi dòng sổ âm số ngày còn lại."""
    await env.give(days=2)
    grant, _ = _admin_cases(env)
    view = await grant.execute(ADMIN, VipGrantCommand(1, "bù sự cố", days=7))
    assert view.vip.vip_until == NOW + timedelta(days=9)
    revoked = await grant.execute(ADMIN, VipGrantCommand(1, "vi phạm", revoke=True))
    assert revoked.vip.is_active is False and revoked.vip.vip_until == NOW
    last = env.uow.wallets.ledger[-1]
    assert (last.amount, last.vip_until_after) == (-9, NOW)
    assert [c[1] for c in env.uow.audit.calls] == ["rewards.vip_granted", "rewards.vip_revoked"]
    with pytest.raises(VipNotActiveError):
        await grant.execute(ADMIN, VipGrantCommand(1, "lần nữa", revoke=True))


async def test_admin_adjust_wallet_double_click_applies_once_and_audits_once(env: Env) -> None:
    """US-QT-18 / F17.10: gửi lại cùng mã yêu cầu (xu, vé) không cộng lần hai, không ghi nhật ký."""
    _, adjust = _admin_cases(env)
    for currency, amount in ((Currency.COIN, 40), (Currency.TICKET, 2)):
        request_id = uuid.uuid4()
        command = WalletAdjustCommand(1, currency, amount, "bù sự cố", request_id)
        first = await adjust.execute(ADMIN, command)
        again = await adjust.execute(ADMIN, command)
        assert (again.coin_balance, again.ticket_balance) == (first.coin_balance, first.ticket_balance)
    wallet = await env.wallet()
    assert (wallet.coin_balance, wallet.ticket_balance) == (40, 2)
    assert len(env.uow.wallets.ledger) == 2 and len(env.uow.audit.calls) == 2
    assert env.notifier.events == [("wallet_adjusted", 1), ("wallet_adjusted", 1)]
    # Mã khác là thao tác khác.
    await adjust.execute(ADMIN, WalletAdjustCommand(1, Currency.COIN, 40, "bù sự cố", uuid.uuid4()))
    assert (await env.wallet()).coin_balance == 80


async def test_admin_vip_grant_and_revoke_double_click_apply_once(env: Env) -> None:
    """US-QT-18 / F17.10: cấp và thu hồi VIP gửi lại cùng mã yêu cầu chỉ có hiệu lực một lần."""
    grant, _ = _admin_cases(env)
    give = VipGrantCommand(1, "bù sự cố", days=7, request_id=uuid.uuid4())
    await grant.execute(ADMIN, give)
    again = await grant.execute(ADMIN, give)
    assert again.vip.vip_until == NOW + timedelta(days=7)
    take = VipGrantCommand(1, "vi phạm", revoke=True, request_id=uuid.uuid4())
    revoked = await grant.execute(ADMIN, take)
    replay = await grant.execute(ADMIN, take)  # thu hồi lại cùng mã: kết quả cũ, không báo "chưa có VIP"
    assert revoked.vip.is_active is False and replay.vip.is_active is False
    assert [c[1] for c in env.uow.audit.calls] == ["rewards.vip_granted", "rewards.vip_revoked"]
    assert len(env.uow.wallets.ledger) == 2
    assert [e[0] for e in env.notifier.events] == ["vip_granted", "vip_revoked"]


async def test_update_reward_item_clears_description_and_limit_with_explicit_null(env: Env) -> None:
    """US-QT-17 / F17.09: null tường minh xóa mô tả và giới hạn mỗi người; trường không gửi thì giữ nguyên."""
    create = CreateRewardItemUseCase(env.factory(), env.clock)
    update = UpdateRewardItemUseCase(env.factory(), env.clock)
    new = CreateItemCommand(
        "vip_9d", "9 ngày VIP", "vip_days", 900, description="mô tả", vip_days=9, per_user_limit=3
    )
    item_id = (await create.execute(ADMIN, new)).item.id
    kept = await update.execute(ADMIN, item_id, {"price_coins": 950})
    assert (kept.item.description, kept.item.per_user_limit) == ("mô tả", 3)
    cleared = await update.execute(ADMIN, item_id, {"description": None, "per_user_limit": None})
    assert (cleared.item.description, cleared.item.per_user_limit) == (None, None)
    for field in ("name", "price_coins", "is_active", "sort_order"):
        with pytest.raises(InvalidRewardError):
            await update.execute(ADMIN, item_id, {field: None})


async def test_admin_vip_grant_validation(env: Env) -> None:
    grant, _ = _admin_cases(env)
    for command in (
        VipGrantCommand(1, "x", days=366),
        VipGrantCommand(1, "x", days=0),
        VipGrantCommand(1, "x"),
        VipGrantCommand(1, "x", days=3, revoke=True),
        VipGrantCommand(1, " ", days=3),
    ):
        with pytest.raises(InvalidRewardError):
            await grant.execute(ADMIN, command)
    with pytest.raises(PermissionDeniedError):
        await grant.execute(ME, VipGrantCommand(1, "x", days=3))


async def test_admin_user_rewards_view_lists_wallet_unlocks_frames_and_ledger(env: Env) -> None:
    """US-QT-18 TC1."""
    env.uow.series.add(12, vip=True)
    await env.give(coins=50, tickets=1, key="a")
    await UnlockSeriesUseCase(env.factory(), env.clock).execute(ME, 12, uuid.uuid4())
    await env.grant().execute(
        GrantCommand(1, RewardBundle(frame=FrameGrant("spring_petal", FrameSource.SEASON)), "f")
    )
    view = await GetUserRewardsUseCase(env.factory(), env.clock).execute(ADMIN, 1, 1, 20)
    assert (view.wallet.coin_balance, view.wallet.ticket_balance) == (50, 0)
    assert [u.unlock.series_id for u in view.unlocks] == [12] and view.unlocks[0].series_title == "Truyện 12"
    assert [f.code for f, _ in view.frames] == ["spring_petal"]
    assert view.ledger.total == 3 and view.ledger.items[0].currency is Currency.TICKET
    with pytest.raises(PermissionDeniedError):
        await GetUserRewardsUseCase(env.factory(), env.clock).execute(ME, 1, 1, 20)
