"""Alembic chạy async. URL lấy từ Settings; đặt biến ALEMBIC_TARGET=test để migrate CSDL kiểm thử."""

from __future__ import annotations

import asyncio
import importlib
import os
import pkgutil
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

import app.modules
from app.core.config import get_settings
from app.core.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _import_orm_models() -> None:
    """Nạp mọi `app.modules.<m>.infrastructure.orm_models` để Base.metadata đủ bảng."""
    for module in pkgutil.iter_modules(app.modules.__path__):
        name = f"app.modules.{module.name}.infrastructure.orm_models"
        try:
            importlib.import_module(name)
        except ModuleNotFoundError as exc:
            if exc.name != name and not name.startswith(f"{exc.name}."):
                raise


_import_orm_models()
target_metadata = Base.metadata


def _database_url() -> str:
    settings = get_settings()
    if os.environ.get("ALEMBIC_TARGET") == "test":
        if not settings.test_database_url:
            raise RuntimeError("Chưa cấu hình TEST_DATABASE_URL")
        return settings.test_database_url
    return settings.database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(), target_metadata=target_metadata, literal_binds=True, compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_sync(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(_database_url())
    async with engine.connect() as connection:
        await connection.run_sync(_run_sync)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
