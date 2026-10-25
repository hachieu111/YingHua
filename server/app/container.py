"""Lắp ghép phụ thuộc dùng chung cho toàn ứng dụng (tạo một lần lúc khởi động)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.clock import Clock, SystemClock
from app.core.config import Settings
from app.core.db import create_engine, create_session_factory
from app.core.rate_limit import FailureLimiter
from app.core.security import TokenService
from app.core.single_flight import SingleFlight
from app.core.storage import FileStorage, LocalFileStorage
from app.core.ttl_cache import TtlCache


@dataclass(slots=True)
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    clock: Clock
    tokens: TokenService
    login_limiter: FailureLimiter
    storage: FileStorage
    single_flight: SingleFlight  # gộp yêu cầu trùng đang chạy (F11.05); phải dùng chung cả tiến trình
    guest_tts_limiter: FailureLimiter
    voices_cache: TtlCache[Any]  # danh sách giọng TTS khả dụng (F11.03), dùng chung cả tiến trình


def build_container(settings: Settings, clock: Clock | None = None) -> Container:
    clock = clock or SystemClock()
    engine = create_engine(settings.database_url, pool_size=settings.db_pool_size, echo=settings.db_echo)
    tokens = TokenService(
        settings.jwt_secret.get_secret_value(), settings.jwt_algorithm, settings.access_token_minutes, clock
    )
    return Container(
        settings=settings,
        engine=engine,
        session_factory=create_session_factory(engine),
        clock=clock,
        tokens=tokens,
        login_limiter=FailureLimiter(timedelta(minutes=settings.login_attempt_window_minutes), clock),
        storage=LocalFileStorage(settings.storage_dir / "files"),
        single_flight=SingleFlight(),
        guest_tts_limiter=FailureLimiter(timedelta(minutes=settings.guest_tts_window_minutes), clock),
        voices_cache=TtlCache(clock),
    )


def get_container(request: Request) -> Container:
    """Dependency FastAPI: lấy container đã tạo trong lifespan."""
    container: Container = request.app.state.container
    return container
