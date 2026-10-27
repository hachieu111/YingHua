"""Tạo phiên đăng nhập mới (cặp mã truy cập + mã làm mới). Dùng chung cho đăng ký, đăng nhập, làm mới."""

from __future__ import annotations

import uuid

from app.core.clock import Clock
from app.core.security import TokenService, hash_token, new_opaque_token
from app.modules.auth.application.dto import AuthConfig, TokenPair
from app.modules.auth.application.ports import AuthUnitOfWork
from app.modules.auth.domain.entities import NewRefreshSession, User


class SessionIssuer:
    def __init__(self, tokens: TokenService, clock: Clock, config: AuthConfig) -> None:
        self._tokens = tokens
        self._clock = clock
        self._config = config

    async def open_session(
        self,
        uow: AuthUnitOfWork,
        user: User,
        user_agent: str | None,
        ip: str | None,
        remember_me: bool = True,
    ) -> TokenPair:
        return await self._issue(uow, user, str(uuid.uuid4()), user_agent, ip, remember_me)

    async def rotate(
        self,
        uow: AuthUnitOfWork,
        user: User,
        family_id: str,
        old_session_id: int,
        user_agent: str | None,
        ip: str | None,
        remember_me: bool = True,
    ) -> TokenPair:
        pair, new_id = await self._issue_with_id(uow, user, family_id, user_agent, ip, remember_me)
        await uow.sessions.mark_replaced(old_session_id, new_id)
        return pair

    async def _issue(
        self,
        uow: AuthUnitOfWork,
        user: User,
        family_id: str,
        user_agent: str | None,
        ip: str | None,
        remember_me: bool,
    ) -> TokenPair:
        pair, _ = await self._issue_with_id(uow, user, family_id, user_agent, ip, remember_me)
        return pair

    async def _issue_with_id(
        self,
        uow: AuthUnitOfWork,
        user: User,
        family_id: str,
        user_agent: str | None,
        ip: str | None,
        remember_me: bool,
    ) -> tuple[TokenPair, int]:
        now = self._clock.now()
        ttl = self._config.refresh_ttl if remember_me else self._config.short_refresh_ttl
        refresh_token = new_opaque_token()
        stored = await uow.sessions.add(
            NewRefreshSession(
                user_id=user.id,
                family_id=family_id,
                token_hash=hash_token(refresh_token),
                expires_at=now + ttl,
                created_at=now,
                user_agent=(user_agent or "")[:255] or None,
                ip=(ip or "")[:64] or None,
            )
        )
        access = self._tokens.issue_access_token(user.id, user.role.value, family_id)
        return TokenPair(access, refresh_token, self._config.access_expires_in, remember_me), stored.id
