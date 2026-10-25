"""Quy tắc thuần của M04: kiểm bong bóng do pipeline ghi, rút gọn lỗi, tên tệp tải về."""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence

from app.modules.imaging.domain.entities import BubbleClass, ImageVariant, NewBubble, Translation
from app.modules.imaging.domain.errors import InvalidBubbleError

MAX_ERROR_MESSAGE_CHARS = 1000
MAX_ERROR_STEP_CHARS = 32
MAX_BUBBLES_PER_PAGE = 500
MAX_RESULT_IMAGE_BYTES = 30 * 1024 * 1024
ORPHAN_RESULT_GRACE_MINUTES = 60  # tệp kết quả vừa lưu nhưng chưa gắn vào bản dịch
MAX_FILENAME_STEM_CHARS = 120

_BUBBLE_CLASSES = frozenset(c.value for c in BubbleClass)
_PATH_CHARS = frozenset('\\/:*?"<>|;%')


def clip_error(step: str, message: str) -> tuple[str, str]:
    """Rút gọn lý do lỗi để vừa cột CSDL; thông điệp chỉ một đoạn văn bản, không có stack trace."""
    clean_step = (step.strip() or "unknown")[:MAX_ERROR_STEP_CHARS]
    first_lines = "\n".join(message.strip().splitlines()[:5])  # bỏ phần traceback dài
    return clean_step, (first_lines or "Lỗi không rõ")[:MAX_ERROR_MESSAGE_CHARS]


def validate_bubbles(bubbles: Sequence[NewBubble]) -> None:
    """Raise InvalidBubbleError nếu dữ liệu bong bóng vi phạm ràng buộc (class, trùng idx, kích thước)."""
    if len(bubbles) > MAX_BUBBLES_PER_PAGE:
        raise InvalidBubbleError(f"Một trang tối đa {MAX_BUBBLES_PER_PAGE} vùng chữ")
    seen: set[int] = set()
    for b in bubbles:
        if b.class_name not in _BUBBLE_CLASSES:
            raise InvalidBubbleError(f"Loại vùng chữ không hợp lệ: {b.class_name[:32]}")
        if b.idx in seen or not 0 <= b.idx <= 32767:
            raise InvalidBubbleError("Thứ tự vùng chữ bị trùng hoặc ngoài khoảng")
        seen.add(b.idx)
        if b.w <= 0 or b.h <= 0 or b.x < 0 or b.y < 0:
            raise InvalidBubbleError("Tọa độ vùng chữ không hợp lệ")
        if not b.text_zh:
            raise InvalidBubbleError("Vùng chữ không có văn bản")


def variant_file_id(
    variant: ImageVariant, original_file_id: int | None, translation: Translation | None
) -> int | None:
    """Mã tệp của dạng ảnh; None nếu dạng đó chưa có."""
    if variant is ImageVariant.ORIGINAL:
        return original_file_id
    if translation is None:
        return None
    return (
        translation.inpainted_file_id if variant is ImageVariant.INPAINTED else translation.rendered_file_id
    )


def _clean(text: str) -> str:
    """Đổi ký tự đường dẫn, khoảng trắng và ký tự điều khiển thành gạch ngang; gộp gạch lặp."""
    mapped = "".join("-" if (c in _PATH_CHARS or c.isspace() or not c.isprintable()) else c for c in text)
    while "--" in mapped:
        mapped = mapped.replace("--", "-")
    return mapped.strip("-_.")


def download_filename(
    series_title: str | None, chapter_number: str | None, page_no: int, variant: str, extension: str
) -> str:
    """Tên tệp gợi ý theo truyện–chương–trang (F04.04); đã bỏ ký tự đường dẫn/điều khiển (có thể có dấu)."""
    parts = [series_title or "anh-tai-len"]
    if chapter_number is not None:
        parts.append(f"ch{chapter_number}")
    parts += [f"p{page_no}", variant]
    stem = _clean("_".join(parts)) or "page"
    return f"{stem[:MAX_FILENAME_STEM_CHARS]}.{extension}"


def ascii_filename(name: str) -> str:
    """Bản chỉ gồm ASCII của tên tệp, cho trình duyệt không đọc được `filename*`."""
    folded = unicodedata.normalize("NFKD", name.replace("đ", "d").replace("Đ", "D"))
    return _clean(folded.encode("ascii", "ignore").decode("ascii")) or "page"
