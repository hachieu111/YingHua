"""Quy tắc thuần của M09: chọn từ theo khả năng nhớ R, chuẩn hóa và chấm đáp án."""

from __future__ import annotations

import math
import random
import unicodedata
from collections.abc import Sequence

from app.core.glosses import short_meaning
from app.modules.quiz.domain.entities import QuestionType, QuizWord

MIN_QUESTION_COUNT = 5
MAX_QUESTION_COUNT = 20
OPTION_COUNT = 4  # số lựa chọn của câu trắc nghiệm dự phòng
OPTION_MAX_CHARS = 60  # phương án/đáp án dạng nghĩa dài hơn sẽ khó đọc và lộ đáp án theo độ dài

# Phân nhóm R (F09.01 bước 3, "đề xuất" theo tài liệu đánh giá Luồng 3): dưới 0,7 là sắp quên/đang học,
# từ 0,9 trở lên là đã nhớ lâu; mục tiêu FSRS mặc định là 0,9.
LOW_R_MAX = 0.7
HIGH_R_MIN = 0.9
LOW_SHARE = 0.6
MEDIUM_SHARE = 0.3  # phần còn lại (~10%) là nhóm R cao

FALLBACK_NOTE = "Đề tạo tự động từ từ điển"
MIXED_NOTE = "Một số câu được tạo tự động từ từ điển"


def _is_han(ch: str) -> bool:
    code = ord(ch)
    return 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF or 0x20000 <= code <= 0x2FA1F


def has_han(text: str) -> bool:
    return any(_is_han(c) for c in text)


def quotas(count: int) -> tuple[int, int, int]:
    """Số từ mục tiêu của nhóm R thấp, trung bình, cao (≈ 60% / 30% / 10%)."""
    low = math.ceil(count * LOW_SHARE)
    medium = min(count - low, round(count * MEDIUM_SHARE))
    return low, medium, count - low - medium


def select_words(scored: Sequence[tuple[QuizWord, float]], count: int, rng: random.Random) -> list[QuizWord]:
    """Chọn tối đa `count` từ: ≈60% R thấp, 30% R trung bình, 10% R cao (F09.01).

    Nhóm thiếu từ được bù bằng các từ còn lại có R thấp nhất; thứ tự kết quả được xáo để các nhóm không
    đứng thành khối. `rng` được tiêm vào để test xác định được.
    """
    count = min(count, len(scored))
    groups: list[list[tuple[QuizWord, float]]] = [[], [], []]
    for item in scored:
        r = item[1]
        groups[0 if r < LOW_R_MAX else 1 if r < HIGH_R_MIN else 2].append(item)
    picked: list[tuple[QuizWord, float]] = []
    leftovers: list[tuple[QuizWord, float]] = []
    for group, quota in zip(groups, quotas(count), strict=True):
        group.sort(key=lambda item: item[0].entry_id)  # cố định thứ tự đầu vào trước khi bốc ngẫu nhiên
        rng.shuffle(group)
        picked.extend(group[:quota])
        leftovers.extend(group[quota:])
    leftovers.sort(key=lambda item: item[1])
    picked.extend(leftovers[: count - len(picked)])
    words = [word for word, _ in picked]
    rng.shuffle(words)
    return words


def option_meaning(text: str | None) -> str:
    """Phương án/đáp án dạng nghĩa: nghĩa ngắn (bỏ ký hiệu từ điển) và không quá `OPTION_MAX_CHARS` ký tự."""
    return short_meaning(text, OPTION_MAX_CHARS)


def normalize_answer(text: str) -> str:
    """NFKC, gộp khoảng trắng, không phân biệt hoa thường."""
    return " ".join(unicodedata.normalize("NFKC", text).split()).casefold()


def _fill_key(text: str) -> str:
    """Khóa so sánh câu điền từ: pinyin (không có chữ Hán) bỏ hẳn khoảng trắng để "nǐ hǎo" = "nǐhǎo"."""
    key = normalize_answer(text)
    return key if has_han(key) else key.replace(" ", "")


def is_correct_answer(
    question_type: QuestionType, user_answer: str | None, correct_answer: str, accepted: Sequence[str]
) -> bool:
    """Chấm một câu (F09.03). Câu chưa trả lời là sai."""
    if user_answer is None or not user_answer.strip():
        return False
    if question_type is QuestionType.MULTIPLE_CHOICE:
        return normalize_answer(user_answer) == normalize_answer(correct_answer)
    wanted = {_fill_key(a) for a in (correct_answer, *accepted)}
    return _fill_key(user_answer) in wanted
