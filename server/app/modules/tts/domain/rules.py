"""Quy tắc thuần của M11: chuẩn hóa văn bản, khóa bộ đệm, giọng, tốc độ, chia câu (F11.01–F11.05)."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.modules.tts.domain.errors import TtsTextEmptyError, TtsTextTooLongError

# Mỗi lần gọi Edge TTS đọc tối đa ngần này ký tự; dài hơn thì chia theo câu rồi ghép (F11.04).
MAX_TTS_CHARS = 500
# Tổng độ dài một yêu cầu; vượt thì từ chối 413 để không bị lạm dụng dịch vụ ngoài.
MAX_REQUEST_CHARS = 2000
# Khách chỉ nghe thử đoạn ngắn (từ/câu).
GUEST_MAX_CHARS = 100
GUEST_WINDOW = timedelta(minutes=10)
# Âm thanh nhỏ hơn mức này coi là rỗng/hỏng (F11.06): một ký tự mp3 cũng vài KB.
MIN_AUDIO_BYTES = 256
MAX_RETRIES = 1
RETRY_BACKOFF_SECONDS = 0.5

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
KNOWN_VOICES = frozenset(
    {
        "zh-CN-XiaoxiaoNeural",
        "zh-CN-XiaoyiNeural",
        "zh-CN-YunxiNeural",
        "zh-CN-YunjianNeural",
        "zh-CN-YunxiaNeural",
        "zh-CN-YunyangNeural",
        "zh-CN-liaoning-XiaobeiNeural",
        "zh-CN-shaanxi-XiaoniNeural",
        "zh-TW-HsiaoChenNeural",
        "zh-TW-HsiaoYuNeural",
        "zh-TW-YunJheNeural",
        "zh-HK-HiuGaaiNeural",
        "zh-HK-HiuMaanNeural",
        "zh-HK-WanLungNeural",
    }
)

# Giọng tiếng Trung khác trong danh sách của dịch vụ (F11.03) cũng được chấp nhận, không chỉ giọng đã biết.
_CHINESE_VOICE = re.compile(r"^zh-[A-Z]{2}(-[A-Za-z]+)?-[A-Za-z]+Neural$")

RATE_MIN = Decimal("0.50")
RATE_MAX = Decimal("1.50")
DEFAULT_RATE = Decimal("1.00")
_CENT = Decimal("0.01")

_STRONG_STOPS = "。！？!?；;…"
_WEAK_STOPS = "，,、：:"


def normalize_text(text: str) -> str:
    """Chuẩn hóa để cùng nội dung ra cùng khóa: NFC và gộp khoảng trắng."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def validate_text(text: str, is_guest: bool) -> None:
    """`text` đã chuẩn hóa. Rỗng -> 400; quá dài -> 413."""
    if not text:
        raise TtsTextEmptyError()
    if len(text) > MAX_REQUEST_CHARS:
        raise TtsTextTooLongError(
            f"Nội dung tối đa {MAX_REQUEST_CHARS} ký tự", details={"max_chars": MAX_REQUEST_CHARS}
        )
    if is_guest and len(text) > GUEST_MAX_CHARS:
        raise TtsTextTooLongError(
            f"Khách chỉ nghe thử tối đa {GUEST_MAX_CHARS} ký tự, hãy đăng nhập để nghe đoạn dài hơn",
            details={"max_chars": GUEST_MAX_CHARS},
        )


def text_digest(text: str) -> str:
    """Phần văn bản của khóa bộ đệm: sha256 của văn bản đã chuẩn hóa (giọng và tốc độ là hai phần còn lại)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_voice(requested: str | None, preferred: str | None) -> tuple[str, bool]:
    """Trả (giọng dùng, đã chuyển về giọng mặc định hay chưa). Ưu tiên giọng yêu cầu, rồi giọng cài đặt."""
    candidate = requested or preferred
    if candidate is None:
        return DEFAULT_VOICE, False
    if candidate in KNOWN_VOICES or _CHINESE_VOICE.match(candidate):
        return candidate, False
    return DEFAULT_VOICE, True


def normalize_rate(rate: Decimal | None) -> Decimal:
    """Đưa tốc độ về khoảng 0,5x–1,5x (giá trị biên gần nhất) và làm tròn 2 chữ số (F11.03)."""
    if rate is None:
        return DEFAULT_RATE
    clamped = min(max(rate, RATE_MIN), RATE_MAX)
    return clamped.quantize(_CENT, rounding=ROUND_HALF_UP)


def edge_rate(rate: Decimal) -> str:
    """Đổi 1.20 thành "+20%" theo định dạng của Edge TTS."""
    percent = int(((rate - 1) * 100).to_integral_value(rounding=ROUND_HALF_UP))
    return f"{percent:+d}%"


def _split_after(text: str, stops: str) -> list[str]:
    pieces: list[str] = []
    buffer = ""
    for char in text:
        buffer += char
        if char in stops:
            pieces.append(buffer)
            buffer = ""
    if buffer:
        pieces.append(buffer)
    return pieces


def _fit(piece: str, max_chars: int) -> list[str]:
    """Cắt một câu quá dài: ưu tiên dấu phẩy, cuối cùng cắt cứng."""
    if len(piece) <= max_chars:
        return [piece]
    parts: list[str] = []
    for clause in _split_after(piece, _WEAK_STOPS):
        if len(clause) <= max_chars:
            parts.append(clause)
        else:
            parts.extend(clause[i : i + max_chars] for i in range(0, len(clause), max_chars))
    return parts


def split_into_chunks(text: str, max_chars: int = MAX_TTS_CHARS) -> list[str]:
    """Chia văn bản dài theo câu thành các đoạn <= max_chars (F11.04); ngắn thì giữ nguyên."""
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    current = ""
    for sentence in _split_after(text, _STRONG_STOPS):
        for piece in _fit(sentence, max_chars):
            if current and len(current) + len(piece) > max_chars:
                chunks.append(current)
                current = ""
            current += piece
    if current:
        chunks.append(current)
    return [chunk.strip() for chunk in chunks if chunk.strip()]
