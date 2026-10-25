"""Gom các router của M03 để `main.py` gắn một lần."""

from __future__ import annotations

from app.modules.library.api.admin_router import admin_router
from app.modules.library.api.chapters_router import router as chapters_router
from app.modules.library.api.files_router import router as files_router
from app.modules.library.api.library_router import router as library_router
from app.modules.library.api.series_router import router as series_router

routers = [series_router, chapters_router, library_router, files_router, admin_router]
