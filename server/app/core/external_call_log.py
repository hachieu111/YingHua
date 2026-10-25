"""Ghi nhật ký gọi LLM vào `external_call_logs` (dùng chung M08 và M09, docs/database-design.md §4.12)."""

from __future__ import annotations

import logging

from sqlalchemy import Integer, String, column, insert, table
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.llm_gemini import LlmCall

logger = logging.getLogger(__name__)

# Tham chiếu chỉ-ghi tới bảng `external_call_logs` (hợp đồng lược đồ, tạo ở migration 0006).
_LOGS = table(
    "external_call_logs",
    column("service", String),
    column("provider", String),
    column("operation", String),
    column("status", String),
    column("latency_ms", Integer),
    column("error_code", String),
)
SERVICE = "llm"  # CHECK của bảng chỉ cho 'llm' | 'tts'; nhà cung cấp cụ thể nằm ở cột `provider`


class SqlLlmCallLogWriter:
    """Ghi bằng giao dịch riêng: lỗi ghi nhật ký không được làm hỏng việc chính. Chỉ ghi dịch vụ, nhà cung
    cấp, thao tác, kết quả, thời gian, mã lỗi — không ghi nội dung hay khóa."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record(self, call: LlmCall) -> None:
        try:
            async with self._session_factory() as session:
                await session.execute(
                    insert(_LOGS).values(
                        service=SERVICE,
                        provider=call.provider,
                        operation=call.operation,
                        status=call.status,
                        latency_ms=call.latency_ms,
                        error_code=call.error_code,
                    )
                )
                await session.commit()
        except SQLAlchemyError:
            logger.warning("Không ghi được nhật ký gọi dịch vụ ngoài", exc_info=True)
