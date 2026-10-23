"""Phát âm tiếng Trung (edge-tts, miễn phí) có cache. Lỗi mạng -> 503, frontend tự dùng Web Speech API."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import User, UserSettings
from ..security import get_current_user
from ..services import storage, tts

router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.get("/voices")
def voices(user: User = Depends(get_current_user)):
    return [{"id": k, "label": v} for k, v in tts.VOICES.items()]


@router.get("")
async def speak(text: str = Query(min_length=1), voice: str | None = None,
                rate: str = Query("+0%", pattern=r"^[+-]\d{1,2}%$"),
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Trả về file mp3. Lần đầu sinh bằng edge-tts, các lần sau lấy từ cache."""
    text = text.strip()
    if len(text) > settings.tts_max_chars:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Tối đa {settings.tts_max_chars} ký tự")
    if voice is None:
        st = db.get(UserSettings, user.id)
        voice = (st.tts_voice if st and st.tts_voice else None) or settings.tts_default_voice
    if voice not in tts.VOICES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Giọng đọc không hỗ trợ")

    f = tts.get_cached(db, text, voice, rate)
    if f is None:
        try:
            audio = await tts.synthesize(text, voice, rate)
        except Exception as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                                f"Dịch vụ phát âm tạm thời lỗi ({type(exc).__name__}). Hãy dùng Web Speech API.")
        f = tts.store(db, text, voice, rate, audio)
    return FileResponse(storage.file_path(f), media_type="audio/mpeg",
                        headers={"Cache-Control": "private, max-age=86400"})
