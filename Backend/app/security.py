"""Mật khẩu (bcrypt), access token (JWT) và refresh token xoay vòng (lưu SHA-256 trong DB)."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import RefreshToken, User

bearer = HTTPBearer(auto_error=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------ password
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode())
    except ValueError:
        return False


# ------------------------------------------------------------------ access token
def create_access_token(user: User) -> str:
    now = utcnow()
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode_access(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Access token đã hết hạn",
                            headers={"WWW-Authenticate": "Bearer"})
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Access token không hợp lệ",
                            headers={"WWW-Authenticate": "Bearer"})
    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sai loại token")
    return payload


# ------------------------------------------------------------------ refresh token
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_refresh_token(db: Session, user: User, request: Request | None,
                        family_id: uuid.UUID | None = None) -> tuple[str, RefreshToken]:
    raw = secrets.token_urlsafe(48)
    row = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(raw),
        family_id=family_id or uuid.uuid4(),
        expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
        user_agent=(request.headers.get("user-agent", "")[:255] if request else None),
        ip=(request.client.host if request and request.client else None),
    )
    db.add(row)
    db.flush()
    return raw, row


def rotate_refresh_token(db: Session, raw: str, request: Request | None) -> tuple[User, str]:
    """Đổi refresh token cũ lấy token mới (cùng family). Phát hiện dùng lại token đã thay thế."""
    row = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw)).with_for_update()
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token không hợp lệ")

    if row.revoked_at is not None:
        if row.replaced_by is not None:
            # Token đã bị xoay mà vẫn được gửi lại -> có thể bị đánh cắp: thu hồi cả phiên đăng nhập
            revoke_family(db, row.family_id)
            db.commit()
            raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                                "Phát hiện refresh token bị dùng lại, phiên đăng nhập đã bị thu hồi")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token đã bị thu hồi")

    if row.expires_at <= utcnow():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token đã hết hạn")

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tài khoản không còn hoạt động")

    new_raw, new_row = issue_refresh_token(db, user, request, family_id=row.family_id)
    row.revoked_at = utcnow()
    row.replaced_by = new_row.id
    return user, new_raw


def revoke_family(db: Session, family_id: uuid.UUID) -> None:
    db.execute(update(RefreshToken)
               .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
               .values(revoked_at=utcnow()))


def revoke_token(db: Session, raw: str, user_id: int) -> bool:
    """Đăng xuất thiết bị hiện tại: thu hồi cả family của token này."""
    row = db.execute(select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw))).scalar_one_or_none()
    if row is None or row.user_id != user_id:
        return False
    revoke_family(db, row.family_id)
    return True


def revoke_all_for_user(db: Session, user_id: int) -> None:
    db.execute(update(RefreshToken)
               .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
               .values(revoked_at=utcnow()))


# ------------------------------------------------------------------ dependencies
def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                     db: Session = Depends(get_db)) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chưa đăng nhập",
                            headers={"WWW-Authenticate": "Bearer"})
    payload = _decode_access(creds.credentials)
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tài khoản không tồn tại hoặc đã bị khoá")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Chỉ admin mới được thực hiện")
    return user
