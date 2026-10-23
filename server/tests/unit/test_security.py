from __future__ import annotations

from datetime import timedelta

import bcrypt
import pytest

from app.core.errors import UnauthenticatedError
from app.core.security import (
    TokenService,
    hash_password,
    hash_token,
    new_opaque_token,
    password_needs_rehash,
    verify_password,
)

SECRET = "x" * 40


def test_argon2_hash_verifies_only_the_right_password() -> None:
    hashed = hash_password("mat-khau-dung")
    assert hashed.startswith("$argon2id$")
    assert verify_password("mat-khau-dung", hashed)
    assert not verify_password("mat-khau-sai", hashed)
    assert not password_needs_rehash(hashed)


def test_legacy_bcrypt_hash_still_verifies_and_needs_rehash() -> None:
    legacy = bcrypt.hashpw(b"mat-khau-cu", bcrypt.gensalt()).decode()
    assert verify_password("mat-khau-cu", legacy)
    assert not verify_password("khac", legacy)
    assert password_needs_rehash(legacy)


def test_garbage_hash_is_rejected_without_raising() -> None:
    assert not verify_password("abc", "khong-phai-hash")


def test_opaque_token_is_random_and_hash_is_stable() -> None:
    a, b = new_opaque_token(), new_opaque_token()
    assert a != b and len(a) >= 64
    assert hash_token(a) == hash_token(a)
    assert len(hash_token(a)) == 64


def test_access_token_round_trip(fixed_clock) -> None:  # type: ignore[no-untyped-def]
    tokens = TokenService(SECRET, "HS256", 15, fixed_clock)
    claims = tokens.decode_access_token(tokens.issue_access_token(user_id=7, role="admin"))
    assert (claims.user_id, claims.role) == (7, "admin")
    assert claims.token_id


def test_access_token_expires_after_ttl(fixed_clock) -> None:  # type: ignore[no-untyped-def]
    tokens = TokenService(SECRET, "HS256", 15, fixed_clock)
    token = tokens.issue_access_token(user_id=1, role="user")
    fixed_clock.at += timedelta(minutes=15, seconds=1)
    with pytest.raises(UnauthenticatedError):
        tokens.decode_access_token(token)


def test_token_signed_with_other_secret_is_rejected(fixed_clock) -> None:  # type: ignore[no-untyped-def]
    forged = TokenService("y" * 40, "HS256", 15, fixed_clock).issue_access_token(1, "admin")
    with pytest.raises(UnauthenticatedError):
        TokenService(SECRET, "HS256", 15, fixed_clock).decode_access_token(forged)
