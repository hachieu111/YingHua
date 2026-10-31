"""Adapter tra từ của M05 gọi qua giao diện công khai của M06 và M02."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import Clock
from app.modules.auth.application.public import Identity
from app.modules.dictionary.application.public import LookupResult, LookupWordUseCase
from app.modules.dictionary.infrastructure.public import PypinyinProvider, SqlDictionaryUnitOfWork
from app.modules.settings.application.public import GetSettingsUseCase
from app.modules.settings.infrastructure.public import SqlSettingsUnitOfWork


class DictionaryLookupAdapter:
    """Tra từ đầy đủ cho người đã đăng nhập (theo cài đặt hiển thị tu tiên của họ), cơ bản cho Khách."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], clock: Clock) -> None:
        self._session_factory = session_factory
        self._pinyin = PypinyinProvider()
        self._clock = clock

    def _lookup_use_case(self) -> LookupWordUseCase:
        def factory() -> SqlDictionaryUnitOfWork:
            return SqlDictionaryUnitOfWork(self._session_factory)

        return LookupWordUseCase(factory, self._pinyin, self._clock)

    async def lookup(
        self, term: str, identity: Identity | None, bubble_id: int | None = None
    ) -> LookupResult:
        include_specialized = True
        if identity is not None:
            settings = await GetSettingsUseCase(lambda: SqlSettingsUnitOfWork(self._session_factory)).execute(
                identity
            )
            include_specialized = settings.show_xianxia
        return await self._lookup_use_case().execute(
            term, identity, include_specialized=include_specialized, bubble_id=bubble_id
        )
