from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from app.core.clock import Clock
from app.core.learning_events import LearningEvent, LearningSource
from app.modules.auth.application.public import Identity
from app.modules.gamification.application.dto import MissedItem, Notice, SessionResult, SubmitRoundCommand
from app.modules.gamification.application.ports import GamificationUnitOfWork, NoticeSender
from app.modules.gamification.application.recorder import EventRecorder
from app.modules.gamification.domain.blade_rules import score_blade
from app.modules.gamification.domain.entities import MinigameRound, NewMinigameSession
from app.modules.gamification.domain.errors import (
    InvalidMinigameResultError,
    MinigameRoundExpiredError,
    MinigameRoundNotFoundError,
    MinigameRoundUsedError,
)
from app.modules.gamification.domain.minigame_rules import (
    MAX_DURATION_MS,
    MIN_DURATION_MS,
    round_deadline,
    server_duration_ms,
)


class SubmitRoundUseCase:
    """F16.01 - Nộp kết quả ván "Gõ pinyin chém chữ" (US-NH-81).

    Máy chủ giữ lượt đã phát: bộ mục và đáp án lấy từ lượt, không nhận điểm/combo từ trình duyệt.
    Lượt của người khác → 404; đã nộp → 409 `MINIGAME_ROUND_USED`; quá hạn (thời gian chơi + dự phòng) →
    409 `MINIGAME_ROUND_EXPIRED`; chuỗi sự kiện vô lý (mục không có/lặp, mốc thời gian lùi hay vượt đồng
    hồ máy chủ, gõ nhanh hơn người thật) → 400 và lượt chưa bị đốt. Điểm, combo, độ chính xác, hạng tính
    lại ở máy chủ. Khóa dòng lượt nên hai yêu cầu đồng thời chỉ một lần được nhận. Lưu ván và cộng XP
    cùng giao dịch.

    XP = min(10, số hit // 2), chỉ 5 ván đầu mỗi ngày được tính (F16.02). Không cộng xu, không đổi lịch ôn.
    """

    def __init__(
        self, uow_factory: Callable[[], GamificationUnitOfWork], notices: NoticeSender, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._notices = notices
        self._clock = clock

    async def execute(self, identity: Identity, command: SubmitRoundCommand) -> SessionResult:
        _validate_client_duration(command)
        uid, now = identity.user_id, self._clock.now()
        pending: list[Notice] = []
        async with self._uow_factory() as uow:
            issued = await uow.minigames.get_round_for_update(command.round_id, uid)
            if issued is None:
                raise MinigameRoundNotFoundError()
            _check_open(issued, now)
            elapsed_ms = server_duration_ms(issued.issued_at, now)
            scored = score_blade(issued.items, command.events, command.typos, elapsed_ms)
            if not await uow.minigames.mark_round_submitted(issued.id, now):
                raise MinigameRoundUsedError()
            previous_best = await uow.minigames.best_score(uid, issued.hsk_band)
            duration_ms = min(command.duration_ms, elapsed_ms, MAX_DURATION_MS)
            row = NewMinigameSession(
                uid,
                issued.hsk_band,
                issued.radical,
                scored.score,
                scored.hits,
                scored.misses,
                command.typos,
                scored.max_combo,
                duration_ms,
                now,
            )
            session = await uow.minigames.add(row)
            event = LearningEvent(uid, LearningSource.MINIGAME, str(session.id), now, value=scored.hits)
            xp = await EventRecorder(uow).record(event, pending)
            await uow.commit()
        for notice in pending:
            await self._notices.send(notice)
        return SessionResult(
            session.id,
            issued.mode,
            issued.hsk_band,
            issued.radical,
            scored.score,
            scored.hits,
            scored.misses,
            command.typos,
            scored.max_combo,
            scored.accuracy,
            scored.rank,
            duration_ms,
            xp,
            scored.score > previous_best,
            [MissedItem(i.text, i.pinyin, i.han_viet) for i in scored.missed],
        )


def _check_open(issued: MinigameRound, now: datetime) -> None:
    if issued.submitted_at is not None:
        raise MinigameRoundUsedError()
    if now > round_deadline(issued.issued_at):
        raise MinigameRoundExpiredError()


def _validate_client_duration(command: SubmitRoundCommand) -> None:
    """Số do trình duyệt đo chỉ để loại ván vô lý; giá trị lưu không vượt số đo của máy chủ."""
    if not MIN_DURATION_MS <= command.duration_ms <= MAX_DURATION_MS:
        raise InvalidMinigameResultError("Thời gian chơi không hợp lệ")
