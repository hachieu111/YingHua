"""Bề mặt công khai của M10 cho module khác (M07 hiện thực nguồn từ đã lưu)."""

from __future__ import annotations

from app.modules.suggestions.application.ports import DismissedRepository, SavedTermSource

__all__ = ["DismissedRepository", "SavedTermSource"]
