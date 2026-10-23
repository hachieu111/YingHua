"""Engine async, session và Unit of Work dùng chung (xem .claude/rules/database.md)."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Tên ràng buộc cố định để Alembic sinh migration ổn định.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Lớp gốc cho ORM model — chỉ dùng ở tầng infrastructure."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def create_engine(url: str, *, pool_size: int, echo: bool) -> AsyncEngine:
    return create_async_engine(url, pool_size=pool_size, pool_pre_ping=True, echo=echo)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


class SqlAlchemyUnitOfWork:
    """Một giao dịch cho một use case. Không gọi commit() thì mọi thay đổi bị rollback khi thoát.

    Module con kế thừa lớp này và gắn repository của mình trong `_init_repositories`.
    """

    session: AsyncSession

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def _init_repositories(self) -> None:
        """Lớp con tạo repository từ `self.session`."""

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self.session = self._session_factory()
        self._init_repositories()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        try:
            await self.session.rollback()  # no-op nếu đã commit
        finally:
            await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
