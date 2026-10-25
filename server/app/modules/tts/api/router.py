"""M11 Phát âm — F11.01, F11.03 (US-NH-53, US-NH-55).

Chọn `POST /tts` (không dùng GET) vì văn bản có thể dài và cần gửi kèm token Bearer: giao diện gọi bằng
`fetch` có header Authorization rồi phát blob, không gắn thẳng URL vào thẻ <audio>.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.modules.auth.api.public import Identity, get_optional_identity
from app.modules.tts.api.dependencies import get_list_voices, get_synthesize_speech
from app.modules.tts.api.schemas import SpeakRequest, VoiceListResponse, VoiceResponse
from app.modules.tts.application.dto import SynthesizeCommand
from app.modules.tts.application.use_cases.list_voices import ListVoicesUseCase
from app.modules.tts.application.use_cases.synthesize_speech import SynthesizeSpeechUseCase

router = APIRouter(prefix="/tts", tags=["M11 Phát âm"])

# Header trả kèm âm thanh; main.py cho phép trình duyệt đọc chúng (CORS expose).
HEADER_VOICE = "X-TTS-Voice"
HEADER_RATE = "X-TTS-Rate"
HEADER_VOICE_FALLBACK = "X-TTS-Voice-Fallback"
HEADER_CACHE = "X-TTS-Cache"
EXPOSED_HEADERS = [HEADER_VOICE, HEADER_RATE, HEADER_VOICE_FALLBACK, HEADER_CACHE]


@router.post(
    "",
    summary="Nghe phát âm từ hoặc câu (F11.01, F11.03)",
    response_class=Response,
    responses={
        200: {
            "description": "Âm thanh MP3. Header: X-TTS-Voice, X-TTS-Rate, "
            "X-TTS-Voice-Fallback (true nếu giọng yêu cầu không khả dụng), X-TTS-Cache (hit|miss).",
            "content": {"audio/mpeg": {"schema": {"type": "string", "format": "binary"}}},
        },
        400: {"description": "TTS_TEXT_EMPTY: văn bản rỗng"},
        413: {"description": "TTS_TEXT_TOO_LONG: văn bản quá dài (Khách giới hạn ngắn hơn)"},
        429: {"description": "TTS_RATE_LIMITED: Khách nghe thử quá nhiều lần"},
        503: {"description": "TTS_UNAVAILABLE hoặc TTS_DISABLED: dịch vụ lỗi / đang tắt"},
    },
)
async def speak(
    body: SpeakRequest,
    request: Request,
    identity: Identity | None = Depends(get_optional_identity),
    use_case: SynthesizeSpeechUseCase = Depends(get_synthesize_speech),
) -> Response:
    client_key = request.client.host if request.client else "unknown"
    result = await use_case.execute(
        SynthesizeCommand(
            text=body.text, identity=identity, client_key=client_key, rate=body.rate, voice=body.voice
        )
    )
    return Response(
        content=result.audio,
        media_type="audio/mpeg",
        headers={
            HEADER_VOICE: result.voice,
            HEADER_RATE: str(result.rate),
            HEADER_VOICE_FALLBACK: "true" if result.voice_fallback else "false",
            HEADER_CACHE: "hit" if result.cache_hit else "miss",
        },
    )


@router.get(
    "/voices",
    response_model=VoiceListResponse,
    summary="Danh sách giọng đọc tiếng Trung khả dụng, có lưu đệm (F11.03)",
    description=(
        "Lấy từ dịch vụ Edge TTS (lọc zh-*), lưu đệm 24 giờ. Dịch vụ lỗi vẫn trả 200 với danh sách mặc định "
        "(`source=default`), không bao giờ trả 503."
    ),
)
async def list_voices(use_case: ListVoicesUseCase = Depends(get_list_voices)) -> VoiceListResponse:
    result = await use_case.execute()
    return VoiceListResponse(
        items=[
            VoiceResponse(
                short_name=v.short_name, locale=v.locale, gender=v.gender, friendly_name=v.friendly_name
            )
            for v in result.voices
        ],
        source=result.source,
    )
