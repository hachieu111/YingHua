from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, exists, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.domain.entities import (
    NewRefreshSession,
    NewUser,
    PasswordResetToken,
    RefreshSession,
    Role,
    User,
    UserStatus,
)
from app.modules.auth.domain.errors import EmailAlreadyUsedError
from app.modules.auth.infrastructure.orm_models import PasswordResetTokenModel, RefreshTokenModel, UserModel


def _user(m: UserModel) -> User:
    return User(
        id=m.id,
        email=m.email,
        password_hash=m.password_hash,
        display_name=m.display_name,
        role=Role(m.role),
        status=UserStatus(m.status),
        created_at=m.created_at,
        chinese_name=m.chinese_name,
        avatar_file_id=m.avatar_file_id,
        avatar_preset=m.avatar_preset,
        show_email=m.show_email,
        show_join_date=m.show_join_date,
        locked_reason=m.locked_reason,
        locked_at=m.locked_at,
        password_changed_at=m.password_changed_at,
        last_login_at=m.last_login_at,
    )


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: int) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return _user(model) if model else None

    async def get_many(self, user_ids: Sequence[int]) -> dict[int, User]:
        if not user_ids:
            return {}
        rows = await self._session.scalars(select(UserModel).where(UserModel.id.in_(set(user_ids))))
        return {m.id: _user(m) for m in rows}

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(func.lower(UserModel.email) == email))
        model = result.scalar_one_or_none()
        return _user(model) if model else None

    async def add(self, new_user: NewUser) -> User:
        model = UserModel(
            email=new_user.email,
            password_hash=new_user.password_hash,
            display_name=new_user.display_name,
            created_at=new_user.created_at,
        )
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise EmailAlreadyUsedError() from exc
        return _user(model)

    async def update(self, user: User) -> None:
        model = await self._session.get(UserModel, user.id)
        if model is None:
            return
        model.password_hash = user.password_hash
        model.display_name = user.display_name
        model.chinese_name = user.chinese_name
        model.avatar_file_id = user.avatar_file_id
        model.avatar_preset = user.avatar_preset
        model.role = user.role.value
        model.status = user.status.value
        model.locked_reason = user.locked_reason
        model.locked_at = user.locked_at
        model.show_email = user.show_email
        model.show_join_date = user.show_join_date
        model.password_changed_at = user.password_changed_at
        model.last_login_at = user.last_login_at
        await self._session.flush()

    async def search(self, query: str | None, offset: int, limit: int) -> tuple[list[User], int]:
        condition = []
        if query and query.strip():
            condition.append(UserModel.email.ilike(f"%{_escape_like(query.strip())}%", escape="\\"))
        total = await self._session.scalar(select(func.count()).select_from(UserModel).where(*condition))
        rows = await self._session.execute(
            select(UserModel).where(*condition).order_by(UserModel.id).offset(offset).limit(limit)
        )
        return [_user(m) for m in rows.scalars()], int(total or 0)


def _session(m: RefreshTokenModel) -> RefreshSession:
    return RefreshSession(
        id=m.id,
        user_id=m.user_id,
        family_id=str(m.family_id),
        token_hash=m.token_hash,
        expires_at=m.expires_at,
        revoked_at=m.revoked_at,
        replaced_by_id=m.replaced_by_id,
        created_at=m.created_at,
    )


def _active(now: datetime) -> list[object]:
    """Điều kiện một mã làm mới còn là mã hiện hành của phiên."""
    return [
        RefreshTokenModel.revoked_at.is_(None),
        RefreshTokenModel.replaced_by_id.is_(None),
        RefreshTokenModel.expires_at > now,
    ]


class SqlSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, new_session: NewRefreshSession) -> RefreshSession:
        model = RefreshTokenModel(
            user_id=new_session.user_id,
            token_hash=new_session.token_hash,
            family_id=uuid.UUID(new_session.family_id),
            expires_at=new_session.expires_at,
            created_at=new_session.created_at,
            user_agent=new_session.user_agent,
            ip=new_session.ip,
        )
        self._session.add(model)
        await self._session.flush()
        return _session(model)

    async def get_by_token_hash(self, token_hash: str) -> RefreshSession | None:
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash).with_for_update()
        )
        model = result.scalar_one_or_none()
        return _session(model) if model else None

    async def mark_replaced(self, session_id: int, replaced_by_id: int) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.id == session_id)
            .values(replaced_by_id=replaced_by_id)
        )

    async def is_family_active(self, family_id: str, now: datetime) -> bool:
        try:
            family = uuid.UUID(family_id)
        except ValueError:
            return False
        found = await self._session.scalar(
            select(exists().where(RefreshTokenModel.family_id == family, *_active(now)))  # type: ignore[arg-type]
        )
        return bool(found)

    async def revoke_family(self, family_id: str, at: datetime) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.family_id == uuid.UUID(family_id), RefreshTokenModel.revoked_at.is_(None)
            )
            .values(revoked_at=at)
        )

    async def revoke_user_sessions(self, user_id: int, at: datetime, except_family: str | None = None) -> int:
        conditions = [RefreshTokenModel.user_id == user_id, *_active(at)]
        if except_family is not None:
            conditions.append(RefreshTokenModel.family_id != uuid.UUID(except_family))
        families = (
            (
                await self._session.execute(select(RefreshTokenModel.family_id).where(*conditions).distinct())  # type: ignore[arg-type]
            )
            .scalars()
            .all()
        )
        if families:
            await self._session.execute(
                update(RefreshTokenModel)
                .where(RefreshTokenModel.family_id.in_(families), RefreshTokenModel.revoked_at.is_(None))
                .values(revoked_at=at)
            )
        return len(families)

    async def delete_expired(self, now: datetime, revoked_before: datetime) -> int:
        rows = await self._session.execute(
            delete(RefreshTokenModel)
            .where(
                or_(
                    RefreshTokenModel.expires_at <= now,
                    RefreshTokenModel.revoked_at < revoked_before,
                )
            )
            .returning(RefreshTokenModel.id)
        )
        return len(rows.all())


class SqlPasswordResetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_id: int, token_hash: str, expires_at: datetime, created_at: datetime) -> None:
        self._session.add(
            PasswordResetTokenModel(
                user_id=user_id, token_hash=token_hash, expires_at=expires_at, created_at=created_at
            )
        )
        await self._session.flush()

    async def get_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        result = await self._session.execute(
            select(PasswordResetTokenModel)
            .where(PasswordResetTokenModel.token_hash == token_hash)
            .with_for_update()
        )
        m = result.scalar_one_or_none()
        if m is None:
            return None
        return PasswordResetToken(
            id=m.id, user_id=m.user_id, token_hash=m.token_hash, expires_at=m.expires_at, used_at=m.used_at
        )

    async def mark_used(self, token_id: int, at: datetime) -> None:
        await self._session.execute(
            update(PasswordResetTokenModel).where(PasswordResetTokenModel.id == token_id).values(used_at=at)
        )

    async def delete_expired(self, now: datetime) -> int:
        rows = await self._session.execute(
            delete(PasswordResetTokenModel)
            .where(PasswordResetTokenModel.expires_at <= now)
            .returning(PasswordResetTokenModel.id)
        )
        return len(rows.all())
