"""YingHua API — đọc truyện tranh Trung đã dịch + học từ vựng.

Chạy (trong thư mục Backend):  python -m uvicorn app.main:app --port 8001
Giao diện test:  http://localhost:8001/      Tài liệu API:  http://localhost:8001/docs
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, select, text

from .config import BACKEND_DIR, settings
from .db import SessionLocal
from .models import RefreshToken, StoredFile
from .routers import admin, auth, dictionary, library, me, review, suggestions, tts, vocab
from .services import storage
from .services.pipeline_runner import worker

if sys.platform.startswith("win"):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("yinghua")


def cleanup_expired() -> dict:
    """Xoá file ảnh upload quá hạn (FK ở các bảng tự SET NULL) và refresh token hết hạn đã lâu."""
    now = datetime.now(timezone.utc)
    removed = 0
    with SessionLocal() as db:
        for f in db.execute(select(StoredFile).where(StoredFile.expires_at < now)).scalars().all():
            try:
                storage.file_path(f).unlink(missing_ok=True)
            except OSError:
                log.warning("Không xoá được file %s", f.storage_key)
                continue
            db.delete(f)
            removed += 1
        tokens = db.execute(delete(RefreshToken).where(RefreshToken.expires_at < now - timedelta(days=1))).rowcount
        db.commit()
    if removed or tokens:
        log.info("Dọn dẹp: %d file hết hạn, %d refresh token cũ", removed, tokens)
    return {"files": removed, "refresh_tokens": tokens}


async def _cleanup_loop():
    while True:
        try:
            await asyncio.to_thread(cleanup_expired)
        except Exception:
            log.exception("Dọn dẹp lỗi")
        await asyncio.sleep(settings.cleanup_interval_minutes * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    worker.start()
    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()


app = FastAPI(title="YingHua API", version="1.0",
              description="Đọc truyện tranh tiếng Trung đã dịch + học từ vựng (sổ tay, flashcard SM-2, gợi ý).",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth.router, me.router, library.router, dictionary.router, vocab.router, review.router,
          suggestions.router, tts.router, admin.router):
    app.include_router(r)


@app.get("/api/health", tags=["system"])
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok", "pipeline": worker.status()}


UI_DIR = BACKEND_DIR / "ui"
if UI_DIR.exists():
    app.mount("/", StaticFiles(directory=UI_DIR, html=True), name="ui")
