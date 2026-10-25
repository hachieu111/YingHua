"""Thẻ mở rộng AI (F08.11, US-NH-75): nội dung, kiểm tra kết quả của LLM và bản dựng từ dữ liệu từ điển.

Thuần Python. Không tin dữ liệu LLM trả về: mọi trường đều được kiểm (security.md); riêng mẹo chiết tự chỉ
được nhắc tới các chữ/thành phần có trong dữ liệu phân rã chữ Hán của M06.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

EXAMPLE_COUNT = 2  # số câu ví dụ trong một thẻ
PHRASE_MIN, PHRASE_MAX = 2, 3  # số cụm từ đi kèm
MAX_SENTENCE_CHARS = 120
MAX_TRANSLATION_CHARS = 300
MAX_PHRASE_CHARS = 24
MAX_MNEMONIC_CHARS = 500
LEVEL_MARGIN = 1  # câu ví dụ được khó hơn trình độ tối đa 1 cấp (như F09.09)
DEFAULT_LEVEL_FOR_UNKNOWN = 1  # chưa khai báo trình độ và từ ngoài HSK: coi như cấp 1


class AiNoteSource(str, Enum):
    LLM = "llm"
    FALLBACK = "fallback"  # ví dụ từ điển và chiết tự dựng từ dữ liệu M06


@dataclass(frozen=True, slots=True)
class AiExample:
    zh: str
    pinyin: str | None = None
    vi: str | None = None


@dataclass(frozen=True, slots=True)
class AiPhrase:
    zh: str
    pinyin: str | None = None
    vi: str | None = None


@dataclass(frozen=True, slots=True)
class AiNoteContent:
    examples: tuple[AiExample, ...] = ()
    mnemonic: str | None = None
    phrases: tuple[AiPhrase, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "examples": [{"zh": e.zh, "pinyin": e.pinyin, "vi": e.vi} for e in self.examples],
            "mnemonic": self.mnemonic,
            "phrases": [{"zh": p.zh, "pinyin": p.pinyin, "vi": p.vi} for p in self.phrases],
        }

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> AiNoteContent:
        """Đọc lại nội dung đã lưu (JSONB); mục hỏng bị bỏ qua thay vì làm lỗi cả thẻ."""
        examples = tuple(
            AiExample(i["zh"], i.get("pinyin"), i.get("vi"))
            for i in data.get("examples") or []
            if isinstance(i, dict) and isinstance(i.get("zh"), str)
        )
        phrases = tuple(
            AiPhrase(i["zh"], i.get("pinyin"), i.get("vi"))
            for i in data.get("phrases") or []
            if isinstance(i, dict) and isinstance(i.get("zh"), str)
        )
        mnemonic = data.get("mnemonic")
        return cls(examples, mnemonic if isinstance(mnemonic, str) and mnemonic else None, phrases)


@dataclass(slots=True)
class AiNote:
    vocab_entry_id: int
    content: AiNoteContent
    source: AiNoteSource
    generated_at: datetime
    regenerate_count: int = 0
    model: str | None = None


@dataclass(frozen=True, slots=True)
class CharParts:
    """Dữ liệu phân rã một chữ (M06): đủ để dựng mẹo chiết tự và kiểm thành phần LLM nhắc tới."""

    ch: str
    han_viet: str | None = None
    radical: str | None = None
    components: tuple[str, ...] = ()


def _is_han(ch: str) -> bool:
    code = ord(ch)
    # Gồm cả bộ thủ Kangxi và bộ thủ bổ sung (⺍, ⻌...) vì mẹo chiết tự hay nhắc tới chúng.
    return (
        0x4E00 <= code <= 0x9FFF
        or 0x3400 <= code <= 0x4DBF
        or 0x2E80 <= code <= 0x2FDF
        or 0x20000 <= code <= 0x2FA1F
    )


def example_difficulty_cap(learner_level: int | None, word_level: int | None) -> int:
    """Độ khó tối đa của câu ví dụ: trình độ + 1; chưa khai báo thì max(cấp của từ, 1) + 1."""
    base = learner_level if learner_level is not None else max(word_level or DEFAULT_LEVEL_FOR_UNKNOWN, 1)
    return base + LEVEL_MARGIN


def allowed_mnemonic_chars(term: str, parts: Iterable[CharParts]) -> frozenset[str]:
    """Chữ Hán mẹo chiết tự được phép nhắc tới: chữ của từ, bộ thủ và thành phần của từng chữ."""
    allowed = {c for c in term if _is_han(c)}
    for p in parts:
        allowed.add(p.ch)
        if p.radical:
            allowed.update(p.radical)
        for component in p.components:
            allowed.update(component)
    return frozenset(c for c in allowed if _is_han(c))


def build_mnemonic(parts: Sequence[CharParts]) -> str | None:
    """Mẹo nhớ chiết tự dựng thẳng từ dữ liệu M06; None khi không chữ nào có dữ liệu (phần này bị ẩn)."""
    lines: list[str] = []
    for p in parts:
        pieces: list[str] = []
        if p.components:
            pieces.append("gồm " + " + ".join(p.components))
        if p.radical and p.radical != p.ch:
            pieces.append(f"bộ {p.radical}")
        if not pieces and not p.han_viet:
            continue
        head = f"{p.ch} (âm Hán Việt: {p.han_viet})" if p.han_viet else p.ch
        lines.append(f"{head} {', '.join(pieces)}".rstrip())
    return "; ".join(lines) + "." if lines else None


def sanitize_mnemonic(raw: object, allowed: frozenset[str], fallback: str | None) -> str | None:
    """Mẹo của LLM nếu mọi chữ Hán nó nhắc tới đều có trong dữ liệu; không thì dùng bản dựng từ dữ liệu.

    Không có dữ liệu phân rã (allowed rỗng) thì không kiểm chứng được nên bỏ hẳn phần này.
    """
    if not allowed:
        return None
    if isinstance(raw, str):
        text = " ".join(raw.split())
        mentioned = {c for c in text if _is_han(c)}
        if text and len(text) <= MAX_MNEMONIC_CHARS and mentioned <= allowed:
            return text
    return fallback


def _text(value: object, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    return text if text and len(text) <= limit else None


def _optional(value: object, limit: int) -> str | None:
    return _text(value, limit) if value is not None else None


def parse_llm_examples(payload: object, term: str) -> list[AiExample]:
    """Câu ví dụ hợp lệ của LLM: có `zh` chứa đúng từ, độ dài vừa phải; mục sai bị bỏ, không trùng nhau."""
    items = payload.get("examples") if isinstance(payload, dict) else None
    result: list[AiExample] = []
    for item in items if isinstance(items, list) else []:
        zh = _text(item.get("zh"), MAX_SENTENCE_CHARS) if isinstance(item, dict) else None
        if zh is None or term not in zh or any(e.zh == zh for e in result):
            continue
        pinyin = _optional(item.get("pinyin"), MAX_SENTENCE_CHARS * 3)
        result.append(AiExample(zh, pinyin, _optional(item.get("vi"), MAX_TRANSLATION_CHARS)))
    return result


def parse_llm_phrases(payload: object, term: str) -> list[AiPhrase]:
    """Cụm từ đi kèm hợp lệ: ngắn, chứa từ đang học, không trùng; tối đa `PHRASE_MAX`."""
    items = payload.get("phrases") if isinstance(payload, dict) else None
    result: list[AiPhrase] = []
    for item in items if isinstance(items, list) else []:
        zh = _text(item.get("zh"), MAX_PHRASE_CHARS) if isinstance(item, dict) else None
        if zh is None or term not in zh or any(p.zh == zh for p in result):
            continue
        pinyin = _optional(item.get("pinyin"), MAX_PHRASE_CHARS * 3)
        result.append(AiPhrase(zh, pinyin, _optional(item.get("vi"), MAX_TRANSLATION_CHARS)))
    return result[:PHRASE_MAX]


def examples_within_level(
    examples: Sequence[AiExample], difficulties: Sequence[int | None], cap: int
) -> list[AiExample]:
    """Giữ câu có độ khó (cấp HSK cao nhất trong câu) đã biết và không vượt `cap`."""
    return [e for e, level in zip(examples, difficulties, strict=True) if level is not None and level <= cap]


def merge_examples(llm: Sequence[AiExample], fallback: Sequence[AiExample]) -> list[AiExample]:
    """Đủ `EXAMPLE_COUNT` câu: ưu tiên câu của LLM đã qua kiểm, thiếu thì bù bằng câu dự phòng từ từ điển."""
    merged = list(llm)[:EXAMPLE_COUNT]
    for example in fallback:
        if len(merged) >= EXAMPLE_COUNT:
            break
        if all(example.zh != m.zh for m in merged):
            merged.append(example)
    return merged
