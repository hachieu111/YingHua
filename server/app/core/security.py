"""Băm mật khẩu (Argon2id), JWT access token và refresh token (xem .claude/rules/security.md)."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta

import bcrypt
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.clock import Clock
from app.core.errors import UnauthenticatedError

_hasher = PasswordHasher()  # mặc định của argon2-cffi là Argon2id


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def _is_legacy_bcrypt(hashed: str) -> bool:
    return hashed.startswith(("$2a$", "$2b$", "$2y$"))


def verify_password(plain: str, hashed: str) -> bool:
    """Đúng/sai, không ném lỗi. Hỗ trợ hash bcrypt của người dùng chép từ hệ thống cũ."""
    if _is_legacy_bcrypt(hashed):
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except ValueError:
            return False
    try:
        return _hasher.verify(hashed, plain)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(hashed: str) -> bool:
    """True nếu nên băm lại bằng Argon2id với tham số hiện hành (gọi sau khi đăng nhập thành công)."""
    return _is_legacy_bcrypt(hashed) or _hasher.check_needs_rehash(hashed)


def new_opaque_token() -> str:
    """Chuỗi ngẫu nhiên cho refresh token / liên kết đặt lại mật khẩu. Chỉ lưu bản băm vào CSDL."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AccessClaims:
    user_id: int
    role: str
    token_id: str


class TokenService:
    """Phát hành và xác minh JWT access token."""

    def __init__(self, secret: str, algorithm: str, access_minutes: int, clock: Clock) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._ttl = timedelta(minutes=access_minutes)
        self._clock = clock

    def issue_access_token(self, user_id: int, role: str) -> str:
        now = self._clock.now()
        payload = {
            "sub": str(user_id),
            "role": role,
            "type": "access",
            "jti": uuid.uuid4().hex,
            "iat": now,
            "exp": now + self._ttl,
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> AccessClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"require": ["sub", "exp", "type"], "verify_exp": False},
            )
        except jwt.PyJWTError as exc:
            raise UnauthenticatedError("Phiên đăng nhập không hợp lệ") from exc
        # Kiểm hạn bằng Clock (thay vì giờ máy) để test được và nhất quán toàn hệ thống.
        if payload.get("type") != "access" or int(payload["exp"]) <= int(self._clock.now().timestamp()):
            raise UnauthenticatedError("Phiên đăng nhập đã hết hạn")
        return AccessClaims(
            user_id=int(payload["sub"]),
            role=str(payload.get("role", "user")),
            token_id=str(payload.get("jti", "")),
        )
