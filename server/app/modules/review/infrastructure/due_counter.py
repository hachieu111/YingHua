"""Đếm thẻ đến hạn cho tác vụ nhắc ôn (F14.04): cùng điều kiện với F08.01."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.review.infrastructure.repositories import SqlCardRepository


class SqlDueCardCounter:
    """`due_at <= now`, thẻ không tạm ngưng, từ còn "Đang học". Người gọi (worker) đã chọn đúng người nhận."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def count_due(self, user_id: int, now: datetime) -> int:
        async with self._session_factory() as session:
            return await SqlCardRepository(session).count_due(user_id, now, None, None)
