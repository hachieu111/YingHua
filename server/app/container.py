"""Lắp ghép phụ thuộc dùng chung cho toàn ứng dụng (tạo một lần lúc khởi động)."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.clock import Clock, SystemClock
from app.core.config import Settings
from app.core.db import create_engine, create_session_factory
from app.core.security import TokenService


@dataclass(slots=True)
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    clock: Clock
    tokens: TokenService


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
    )


def get_container(request: Request) -> Container:
    """Dependency FastAPI: lấy container đã tạo trong lifespan."""
    container: Container = request.app.state.container
    return container
