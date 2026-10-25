"""F06.03 — Chọn nghĩa chuyên ngành tu tiên thật sự khác nghĩa thông thường.

Bộ VietPhrase/Names chứa cả từ thông dụng lẫn thuật ngữ tu tiên. Để "từ không phải thuật ngữ tu tiên thì
không hiện mục chuyên ngành", chỉ giữ mục khi: là tên riêng, hoặc từ chưa có nghĩa thông thường,
hoặc nghĩa của nó không trùng nghĩa thông thường nào. [Đề xuất]
"""

from __future__ import annotations

from collections.abc import Sequence

from app.modules.dictionary.domain.entities import SpecializedMeaning


def select_specialized(
    candidates: Sequence[SpecializedMeaning], general_glosses: Sequence[str]
) -> list[SpecializedMeaning]:
    haystack = " ".join(general_glosses).lower()
    selected: list[SpecializedMeaning] = []
    for item in candidates:
        if item.kind == "name" or not haystack:
            selected.append(item)
            continue
        if not any(meaning.strip().lower() in haystack for meaning in item.meanings if meaning.strip()):
            selected.append(item)
    return selected
