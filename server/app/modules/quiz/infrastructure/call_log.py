from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.external_call_log import SqlLlmCallLogWriter
from app.core.llm_gemini import LlmCall
from app.modules.quiz.application.ports import ExternalCall


class SqlLlmCallLog:
    """Ghi nhật ký gọi LLM của M09 (`external_call_logs`) qua bộ ghi dùng chung ở `app.core`."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._writer = SqlLlmCallLogWriter(session_factory)

    async def record(self, call: ExternalCall) -> None:
        await self._writer.record(
            LlmCall(call.provider, call.operation, call.status, call.latency_ms, call.error_code)
        )
