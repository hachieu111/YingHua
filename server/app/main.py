"""Điểm vào ứng dụng FastAPI.

Chạy: `uvicorn app.main:create_app --factory --port 8000` (trong thư mục server/).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.container import build_container
from app.core.config import Settings, get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import REQUEST_ID_HEADER, configure_logging, request_id_middleware
from app.health import router as health_router
from app.modules.admin.api.router import router as admin_users_router
from app.modules.auth.api.router import account_router, auth_router
from app.modules.dictionary.api.router import admin_router as dictionary_admin_router
from app.modules.dictionary.api.router import router as dictionary_router
from app.modules.imaging.api.router import admin_router as imaging_admin_router
from app.modules.imaging.api.router import router as imaging_router
from app.modules.jobs.api.router import router as jobs_router
from app.modules.library.api.router import routers as library_routers
from app.modules.quiz.api.admin_router import admin_router as quiz_admin_router
from app.modules.quiz.api.router import router as quiz_router
from app.modules.reader.api.admin_router import admin_router as reader_admin_router
from app.modules.reader.api.router import router as reader_router
from app.modules.review.api.admin_router import admin_router as review_admin_router
from app.modules.review.api.ai_note_router import router as ai_note_router
from app.modules.review.api.router import router as review_router
from app.modules.settings.api.admin_router import admin_router as settings_admin_router
from app.modules.settings.api.router import router as settings_router
from app.modules.suggestions.api.router import router as suggestions_router
from app.modules.tts.api.router import EXPOSED_HEADERS as TTS_HEADERS
from app.modules.tts.api.router import router as tts_router
from app.modules.vocab.api.admin_router import admin_router as vocab_admin_router
from app.modules.vocab.api.router import router as vocab_router
from app.modules.vocab.api.sentences_router import admin_router as sentences_admin_router
from app.modules.vocab.api.sentences_router import page_words_router, sentences_router

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_json)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = build_container(settings)
        app.state.container = container
        try:
            yield
        finally:
            await container.engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url=f"{API_PREFIX}/docs",
        openapi_url=f"{API_PREFIX}/openapi.json",
    )
    app.middleware("http")(request_id_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER, *TTS_HEADERS],
    )
    register_exception_handlers(app)
    app.include_router(health_router, prefix=API_PREFIX)
    for router in (
        auth_router,
        account_router,
        settings_router,
        admin_users_router,
        settings_admin_router,
        vocab_admin_router,
        sentences_admin_router,
        review_admin_router,
        quiz_admin_router,
        reader_admin_router,
        dictionary_router,
        dictionary_admin_router,
        # Phải đứng trước truyện của M03: `/series/recommendations` không được rơi vào `/series/{series_id}`.
        suggestions_router,
        *library_routers,
        imaging_router,
        imaging_admin_router,
        reader_router,
        vocab_router,
        sentences_router,
        page_words_router,
        review_router,
        ai_note_router,
        quiz_router,
        tts_router,
        jobs_router,
    ):
        app.include_router(router, prefix=API_PREFIX)
    return app
