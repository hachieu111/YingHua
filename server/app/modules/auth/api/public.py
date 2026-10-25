"""Dependency xác thực mà router của module khác được dùng (F01.09)."""

from __future__ import annotations

from app.modules.auth.api.dependencies import get_identity, get_optional_identity, require_admin
from app.modules.auth.application.dto import Identity

__all__ = ["Identity", "get_identity", "get_optional_identity", "require_admin"]
