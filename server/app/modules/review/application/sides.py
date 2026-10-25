"""F08.03 — Nội dung hai mặt của ba loại thẻ."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.review.application.dto import EntryFace
from app.modules.review.domain.entities import CardType


@dataclass(frozen=True, slots=True)
class CardSide:
    """Một mặt thẻ; trường rỗng nghĩa là mặt đó không hiện thông tin ấy."""

    term: str | None = None
    pinyin: str | None = None
    meaning_vi: str | None = None
    sino_vietnamese: str | None = None
    audio_text: str | None = None  # chữ cần phát âm (thẻ nghe, qua M11)
    sentence_vi: str | None = None  # câu dịch của ngữ cảnh mới nhất (gợi ý dự phòng của thẻ recall)
    hint_source: str | None = None  # nguồn gợi ý của mặt trước thẻ recall; các thẻ khác: None


HINT_MEANING = "meaning"
HINT_CONTEXT_SENTENCE = "context_sentence"
HINT_SINO_VIETNAMESE = "sino_vietnamese"
HINT_PINYIN = "pinyin"


def _recall_front(face: EntryFace) -> CardSide:
    """Mặt trước thẻ recall (Việt -> Hán). Thiếu `meaning_vi` thì KHÔNG đoán nghĩa mà lấy gợi ý dự phòng
    theo thứ tự: câu dịch của ngữ cảnh mới nhất -> âm Hán Việt -> pinyin; `hint_source` để giao diện ghi
    đúng nhãn. Giữ đủ 3 thẻ cho mọi từ (F08.03) nên không bỏ thẻ recall của từ thiếu nghĩa."""
    if face.meaning_vi:
        return CardSide(meaning_vi=face.meaning_vi, hint_source=HINT_MEANING)
    sentence = face.context.sentence_vi if face.context else None
    if sentence:
        return CardSide(sentence_vi=sentence, hint_source=HINT_CONTEXT_SENTENCE)
    if face.sino_vietnamese:
        return CardSide(sino_vietnamese=face.sino_vietnamese, hint_source=HINT_SINO_VIETNAMESE)
    if face.pinyin:
        return CardSide(pinyin=face.pinyin, hint_source=HINT_PINYIN)
    return CardSide()


def sides_for(card_type: CardType, face: EntryFace) -> tuple[CardSide, CardSide]:
    """(mặt trước, mặt sau). Ảnh ngữ cảnh và ghi chú nằm ở mặt sau của mọi loại thẻ (F08.04)."""
    if card_type is CardType.RECOGNITION:  # Hán -> Việt
        front = CardSide(term=face.term)
        back = CardSide(face.term, face.pinyin, face.meaning_vi, face.sino_vietnamese)
    elif card_type is CardType.RECALL:  # Việt -> Hán
        front = _recall_front(face)
        back = CardSide(term=face.term, pinyin=face.pinyin, sino_vietnamese=face.sino_vietnamese)
    else:  # nghe -> Hán: mặt trước không lộ chữ Hán
        front = CardSide(audio_text=face.term)
        back = CardSide(face.term, face.pinyin, face.meaning_vi, face.sino_vietnamese)
    return front, back
