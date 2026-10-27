from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.review.domain.fsrs_profile import FsrsProfile
from app.modules.review.infrastructure.orm_models import FsrsParametersModel as Params
from app.modules.review.infrastructure.orm_models import ReviewLogModel


class SqlFsrsProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: int) -> FsrsProfile | None:
        model = await self._session.get(Params, user_id)
        if model is None:
            return None
        return FsrsProfile(tuple(float(w) for w in model.weights), float(model.desired_retention))

    async def save(self, user_id: int, profile: FsrsProfile, review_count: int, now: datetime) -> None:
        values = {
            "weights": list(profile.weights),
            "desired_retention": profile.desired_retention,
            "review_count": review_count,
            "optimized_at": now,
        }
        stmt = insert(Params).values(user_id=user_id, **values)
        await self._session.execute(stmt.on_conflict_do_update(index_elements=[Params.user_id], set_=values))

    async def users_to_optimize(
        self, min_reviews: int, min_new_reviews: int, stale_before: datetime, limit: int
    ) -> list[int]:
        counts = (
            select(ReviewLogModel.user_id.label("uid"), func.count().label("n"))
            .group_by(ReviewLogModel.user_id)
            .having(func.count() >= min_reviews)
            .subquery()
        )
        stmt = (
            select(counts.c.uid)
            .outerjoin(Params, Params.user_id == counts.c.uid)
            .where(
                or_(
                    Params.user_id.is_(None),
                    and_(
                        Params.optimized_at < stale_before,
                        counts.c.n >= Params.review_count + min_new_reviews,
                    ),
                )
            )
            .order_by(Params.optimized_at.asc().nulls_first(), counts.c.uid)
            .limit(limit)
        )
        return [int(uid) for uid in await self._session.scalars(stmt)]
