"""Dependency công khai của M13 cho router quản trị của module khác."""

from __future__ import annotations

from app.modules.admin.api.dependencies import build_ensure_target, get_target_user_id

__all__ = ["build_ensure_target", "get_target_user_id"]
