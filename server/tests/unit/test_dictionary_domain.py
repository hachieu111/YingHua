"""M06 — cấp HSK, câu ví dụ, nghĩa tu tiên, từ loại (F06.01, F06.03, F06.08; US-NH-26…28)."""

from __future__ import annotations

from app.modules.dictionary.domain.entities import SpecializedMeaning
from app.modules.dictionary.domain.examples import MAX_EXAMPLES_PER_ENTRY, extract_examples
from app.modules.dictionary.domain.hsk import NOT_IN_HSK, HskSource, resolve_hsk
from app.modules.dictionary.domain.pos import pos_labels
from app.modules.dictionary.domain.specialized import select_specialized


def test_resolve_hsk_uses_list_when_word_present() -> None:
    info = resolve_hsk("学习", {"学习": 2, "学": 1, "习": 5})
    assert (info.level, info.source) == (2, HskSource.LIST)


def test_resolve_hsk_derives_highest_level_from_characters() -> None:
    info = resolve_hsk("学习", {"学": 1, "习": 4})
    assert (info.level, info.source) == (4, HskSource.DERIVED)


def test_resolve_hsk_ignores_characters_without_level() -> None:
    info = resolve_hsk("学习", {"学": 3})
    assert (info.level, info.source) == (3, HskSource.DERIVED)


def test_resolve_hsk_single_missing_char_is_outside_hsk() -> None:
    assert resolve_hsk("龘", {}) == NOT_IN_HSK
    assert NOT_IN_HSK.source is HskSource.NONE and NOT_IN_HSK.level is None


def test_resolve_hsk_no_characters_known_is_outside_hsk() -> None:
    assert resolve_hsk("龘龘", {"学": 1}) == NOT_IN_HSK


def test_extract_examples_from_thienchuu_gloss() -> None:
    gloss = "[nhất cộng] Tất cả, tổng cộng, hết thảy: 一共多少 人？ Tất cả có bao nhiêu người?;"
    examples = extract_examples(gloss)
    assert len(examples) == 1
    zh, vi = examples[0]
    assert zh.replace(" ", "").startswith("一共多少人")
    assert zh.endswith("？")
    assert vi == "Tất cả có bao nhiêu người?"


def test_extract_examples_second_real_gloss() -> None:
    gloss = (
        "[nhất nhất] Từng người (cái, việc) một, tất cả, hết cả: "
        "無法一一介紹 Không thể giới thiệu từng người được;"
    )
    assert extract_examples(gloss) == [("無法一一介紹", "Không thể giới thiệu từng người được")]


def test_extract_examples_returns_empty_without_example() -> None:
    assert extract_examples("[học] Học tập, bắt chước") == []
    assert extract_examples("") == []


def test_extract_examples_is_capped() -> None:
    gloss = "; ".join(f"[x] nghĩa: 我们学习汉语 Chúng ta học tiếng Hán {n}" for n in "abcdef")
    assert len(extract_examples(gloss)) == MAX_EXAMPLES_PER_ENTRY == 3


def test_select_specialized_keeps_names_and_new_meanings_only() -> None:
    name = SpecializedMeaning("name", ("Diệp Phàm",))
    same = SpecializedMeaning("phrase", ("học tập",))
    new = SpecializedMeaning("phrase", ("đạo tâm",))
    general = ["Học tập, bắt chước"]
    assert select_specialized([name, same, new], general) == [name, new]


def test_select_specialized_keeps_all_when_no_general_meaning() -> None:
    items = [SpecializedMeaning("phrase", ("kim đan",))]
    assert select_specialized(items, []) == items


def test_pos_labels_maps_codes_and_dedupes() -> None:
    assert pos_labels("v,vn") == ("động từ", "danh động từ")
    assert pos_labels("n, n") == ("danh từ",)
    assert pos_labels("zz") == ("zz",)
    assert pos_labels(None) == () and pos_labels("") == ()
