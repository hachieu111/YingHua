from __future__ import annotations

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.tts.application.ports import ExternalCallEntry
from app.modules.tts.infrastructure.orm_models import ExternalCallLogModel

logger = logging.getLogger(__name__)


class SqlExternalCallLog:
    """Ghi `external_call_logs` bằng giao dịch riêng: lỗi ghi nhật ký không được làm hỏng việc chính."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record(self, entry: ExternalCallEntry) -> None:
        try:
            async with self._session_factory() as session:
                session.add(
                    ExternalCallLogModel(
                        service="tts",
                        provider=entry.provider,
                        operation=entry.operation,
                        status=entry.status.value,
                        latency_ms=entry.latency_ms,
                        error_code=entry.error_code,
                    )
                )
                await session.commit()
        except SQLAlchemyError:
            logger.warning("Không ghi được nhật ký gọi dịch vụ ngoài", exc_info=True)
