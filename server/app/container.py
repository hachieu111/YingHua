"""Lắp ghép phụ thuộc dùng chung cho toàn ứng dụng (tạo một lần lúc khởi động)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.ai_policy import AiPolicies
from app.core.clock import Clock, SystemClock
from app.core.config import Settings
from app.core.db import create_engine, create_session_factory
from app.core.rate_limit import FailureLimiter
from app.core.security import TokenService
from app.core.single_flight import SingleFlight
from app.core.storage import FileStorage, LocalFileStorage
from app.core.ttl_cache import TtlCache
from app.core.welcome_gift import WelcomeGiftPort
from app.modules.admin.application.system_settings import CachedSystemSettings, defaults_from_settings
from app.modules.admin.infrastructure.public import SqlSystemSettingsSource
from app.modules.gamification.application.ports import NoticeSender
from app.modules.gamification.infrastructure.public import build_notice_sender
from app.modules.rewards.application.public import GrantWelcomeGiftUseCase, build_ai_policies
from app.modules.rewards.infrastructure.public import (
    SqlRewardsUnitOfWork,
    SqlVipStatusReader,
    build_reward_notifier,
)


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
    system_settings: CachedSystemSettings  # cấu hình hệ thống do quản trị đặt (F13.05), đệm vài giây
    ai_policies: AiPolicies  # công tắc + hạn mức LLM theo tính năng, nâng khi đang VIP (F17.04)
    welcome_gift: WelcomeGiftPort  # quà chào mừng cho tài khoản mới (F01.01, F17.03)
    notices: NoticeSender  # thông báo trong ứng dụng của M16 (gửi sau khi giao dịch thưởng đã lưu, F14.05)


def build_container(settings: Settings, clock: Clock | None = None) -> Container:
    clock = clock or SystemClock()
    engine = create_engine(settings.database_url, pool_size=settings.db_pool_size, echo=settings.db_echo)
    session_factory = create_session_factory(engine)
    tokens = TokenService(
        settings.jwt_secret.get_secret_value(), settings.jwt_algorithm, settings.access_token_minutes, clock
    )
    system_settings = CachedSystemSettings(
        lambda: SqlSystemSettingsSource(session_factory), defaults_from_settings(settings), clock
    )
    return Container(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        clock=clock,
        tokens=tokens,
        login_limiter=FailureLimiter(timedelta(minutes=settings.login_attempt_window_minutes), clock),
        storage=LocalFileStorage(settings.storage_dir / "files"),
        single_flight=SingleFlight(),
        guest_tts_limiter=FailureLimiter(timedelta(minutes=settings.guest_tts_window_minutes), clock),
        voices_cache=TtlCache(clock),
        system_settings=system_settings,
        ai_policies=build_ai_policies(system_settings, SqlVipStatusReader(session_factory), clock),
        welcome_gift=GrantWelcomeGiftUseCase(
            lambda: SqlRewardsUnitOfWork(session_factory),
            clock,
            build_reward_notifier(session_factory, settings.storage_dir / "outbox", clock),
        ),
        notices=build_notice_sender(session_factory, clock),
    )


def get_container(request: Request) -> Container:
    """Dependency FastAPI: lấy container đã tạo trong lifespan."""
    container: Container = request.app.state.container
    return container
