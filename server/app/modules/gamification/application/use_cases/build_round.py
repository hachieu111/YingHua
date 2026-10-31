from __future__ import annotations

import random
import uuid
from collections.abc import Callable

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.gamification.application.dto import BuildRoundCommand, RoundView
from app.modules.gamification.application.ports import GamificationUnitOfWork
from app.modules.gamification.domain.blade_rules import (
    BOSS_EVERY,
    ITEMS_PER_ROUND,
    LIVES,
    MODE_HSK,
    build_items,
    validate_round_request,
)
from app.modules.gamification.domain.entities import CharRow, MinigameRound, WordRow
from app.modules.gamification.domain.minigame_rules import GAME_SECONDS, max_hsk_level

CHAR_CANDIDATES = ITEMS_PER_ROUND + ITEMS_PER_ROUND // 4  # dư để bù chữ không dựng được đáp án
BOSS_CANDIDATES = ITEMS_PER_ROUND // BOSS_EVERY * 3


class BuildRoundUseCase:
    """F16.01 - Dựng bộ 100 mục cho một ván "Gõ pinyin chém chữ" (US-NH-81).

    Chế độ `hsk`: chữ đơn của đúng cấp HSK (chữ mới của cấp đó trước, thiếu thì bù chữ cấp thấp hơn).
    Chế độ `weak_radical`: chữ có bộ thủ đã chọn từ Sổ tay và HSK không vượt trình độ + 1. Khoảng 1/10 mục là
    từ boss hai chữ. Mỗi mục kèm đáp án a-z (ü sinh cả `v` và `u`, chữ đa âm nhận mọi âm). Thiếu dữ liệu
    (dưới 20 mục) → 409, không bắt đầu ván. Máy chủ lưu lượt (bộ mục + giờ phát) để khi nộp kết quả chỉ chấm
    trên bộ mục đã phát. Ván không ảnh hưởng thẻ FSRS.
    """

    def __init__(
        self,
        uow_factory: Callable[[], GamificationUnitOfWork],
        clock: Clock,
        rng: random.Random | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._rng = rng or random.Random()

    async def execute(self, identity: Identity, command: BuildRoundCommand) -> RoundView:
        validate_round_request(command.mode, command.hsk_band, command.radical)
        async with self._uow_factory() as uow:
            chars, words = await self._candidates(uow, identity.user_id, command)
            items = build_items(chars, words, self._rng)
            round_id = uuid.uuid4()
            band = command.hsk_band if command.mode == MODE_HSK else None
            radical = None if command.mode == MODE_HSK else command.radical
            issued = MinigameRound(
                round_id, identity.user_id, command.mode, band, radical, items, self._clock.now(), None
            )
            await uow.minigames.add_round(issued)
            await uow.commit()
        return RoundView(round_id, command.mode, band, radical, GAME_SECONDS, LIVES, items)

    @staticmethod
    async def _candidates(
        uow: GamificationUnitOfWork, user_id: int, command: BuildRoundCommand
    ) -> tuple[list[CharRow], list[WordRow]]:
        if command.mode == MODE_HSK and command.hsk_band is not None:
            band = command.hsk_band
            return (
                await uow.chars.band_chars(band, CHAR_CANDIDATES),
                await uow.chars.band_words(band, BOSS_CANDIDATES),
            )
        radical = command.radical or ""
        profile = await uow.users.profile(user_id)
        level = max_hsk_level(profile.hsk_level)
        return (
            await uow.chars.radical_chars(user_id, radical, level, CHAR_CANDIDATES),
            await uow.chars.radical_words(radical, level, BOSS_CANDIDATES),
        )
