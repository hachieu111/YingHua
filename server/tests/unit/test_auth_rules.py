from __future__ import annotations

import pytest

from app.modules.auth.domain.errors import DisplayNameRequiredError, WeakPasswordError
from app.modules.auth.domain.rules import (
    clean_display_name,
    default_display_name,
    normalize_email,
    validate_password,
)


def test_normalize_email_lowercases_and_strips() -> None:
    assert normalize_email("  Hoc.Vien@Example.COM ") == "hoc.vien@example.com"


@pytest.mark.parametrize("password", ["", "1234567", "x" * 129])
def test_validate_password_rejects_out_of_range(password: str) -> None:
    with pytest.raises(WeakPasswordError):
        validate_password(password)


@pytest.mark.parametrize("password", ["12345678", "x" * 128])
def test_validate_password_accepts_boundaries(password: str) -> None:
    validate_password(password)


def test_display_name_is_trimmed_truncated_and_required() -> None:
    assert clean_display_name("  An  ") == "An"
    assert len(clean_display_name("a" * 300)) == 100
    with pytest.raises(DisplayNameRequiredError):
        clean_display_name("   ")


def test_default_display_name_uses_email_local_part() -> None:
    assert default_display_name("sakura@yinghua.vn") == "sakura"
