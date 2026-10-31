from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gamification.domain.blade_rules import MODE_HSK, MODE_WEAK_RADICAL
from app.modules.gamification.domain.entities import (
    BladeBest,
    BladeItem,
    MinigameRound,
    MinigameSession,
    NewMinigameSession,
)
from app.modules.gamification.domain.minigame_rules import GAME_TYPE
from app.modules.gamification.infrastructure.orm_models import MinigameRoundModel, MinigameSessionModel


def _item_to_json(item: BladeItem) -> dict[str, Any]:
    return {
        "index": item.index,
        "text": item.text,
        "pinyin": item.pinyin,
        "answers": list(item.answers),
        "han_viet": item.han_viet,
        "hsk_level": item.hsk_level,
        "is_boss": item.is_boss,
    }


def _item_from_json(data: dict[str, Any]) -> BladeItem:
    return BladeItem(
        int(data["index"]),
        str(data["text"]),
        str(data["pinyin"]),
        tuple(str(a) for a in data["answers"]),
        data["han_viet"],
        data["hsk_level"],
        bool(data["is_boss"]),
    )


class SqlMinigameRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_round(self, round_: MinigameRound) -> None:
        self._session.add(
            MinigameRoundModel(
                id=round_.id,
                user_id=round_.user_id,
                mode=round_.mode,
                hsk_band=round_.hsk_band,
                radical=round_.radical,
                items=[_item_to_json(i) for i in round_.items],
                issued_at=round_.issued_at,
                submitted_at=None,
            )
        )
        await self._session.flush()

    async def get_round_for_update(self, round_id: uuid.UUID, user_id: int) -> MinigameRound | None:
        model = await self._session.scalar(
            select(MinigameRoundModel)
            .where(MinigameRoundModel.id == round_id, MinigameRoundModel.user_id == user_id)
            .with_for_update()
        )
        if model is None:
            return None
        return MinigameRound(
            model.id,
            model.user_id,
            model.mode,
            model.hsk_band,
            model.radical,
            [_item_from_json(i) for i in model.items],
            model.issued_at,
            model.submitted_at,
        )

    async def purge_rounds_before(self, cutoff: datetime, limit: int) -> int:
        oldest = (
            select(MinigameRoundModel.id)
            .where(MinigameRoundModel.issued_at < cutoff)
            .order_by(MinigameRoundModel.issued_at)
            .limit(limit)
        )
        result = await self._session.execute(
            delete(MinigameRoundModel).where(MinigameRoundModel.id.in_(oldest))
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def mark_round_submitted(self, round_id: uuid.UUID, now: datetime) -> bool:
        result = await self._session.execute(
            update(MinigameRoundModel)
            .where(MinigameRoundModel.id == round_id, MinigameRoundModel.submitted_at.is_(None))
            .values(submitted_at=now)
        )
        return bool(getattr(result, "rowcount", 0) == 1)

    async def add(self, session: NewMinigameSession) -> MinigameSession:
        model = MinigameSessionModel(
            user_id=session.user_id,
            game_type=GAME_TYPE,
            target_radical=session.target_radical,
            hsk_band=session.hsk_band,
            score=session.score,
            correct=session.correct,
            wrong=session.wrong,
            typos=session.typos,
            max_combo=session.max_combo,
            duration_ms=session.duration_ms,
            played_at=session.played_at,
        )
        self._session.add(model)
        await self._session.flush()
        return MinigameSession(model.id, model.user_id, model.score)

    async def best_score(self, user_id: int, hsk_band: int | None) -> int:
        best = await self._session.scalar(
            select(func.max(MinigameSessionModel.score)).where(
                MinigameSessionModel.user_id == user_id,
                MinigameSessionModel.game_type == GAME_TYPE,
                MinigameSessionModel.hsk_band.is_not_distinct_from(hsk_band),
            )
        )
        return int(best or 0)

    async def best_records(self, user_id: int) -> list[BladeBest]:
        rows = await self._session.execute(
            select(
                MinigameSessionModel.hsk_band,
                func.max(MinigameSessionModel.score),
                func.max(MinigameSessionModel.max_combo),
                func.count(),
            )
            .where(MinigameSessionModel.user_id == user_id, MinigameSessionModel.game_type == GAME_TYPE)
            .group_by(MinigameSessionModel.hsk_band)
            .order_by(MinigameSessionModel.hsk_band.asc().nulls_last())
        )
        return [
            BladeBest(
                MODE_WEAK_RADICAL if band is None else MODE_HSK, band, int(score), int(combo), int(plays)
            )
            for band, score, combo, plays in rows
        ]
