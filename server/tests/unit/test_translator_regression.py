"""Hồi quy bộ dịch tu tiên của module ảnh: chữ Việt do LuatNhan chèn không bị tách từng chữ cái,
luật nhân không khớp quá rộng làm sai nghĩa (在…身上 với 现在, 跟…说话, 把…当做, 比…高的多).

Liên quan F04 (xử lý ảnh — bước dịch). Gọi `TranslationEngine` thật với từ điển tu tiên,
không nạp YOLO/PaddleOCR; tự bỏ qua nếu máy không có module ảnh hoặc thư mục từ điển.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
IMAGE_MODULE_ROOT = REPO_ROOT / "module xử lí ảnh"
TRANSLATOR_FILE = IMAGE_MODULE_ROOT / "mudule xu ly anh" / "src" / "translator.py"
DICT_DIR = IMAGE_MODULE_ROOT / "từ điển tu tiên"
DICT_FILES = ("Names.txt", "VietPhrase.txt", "LuatNhan.txt", "PhienAm.txt")

# >= 3 token một chữ cái liền nhau, vd. "t r ê n" — dấu hiệu cụm chữ Việt bị tách từng ký tự.
SPLIT_LETTERS_RE = re.compile(r"(?<!\S)[^\W\d_](?: [^\W\d_]){2,}(?!\S)")


def _load_translator_module() -> ModuleType:
    # Tên module riêng để không đụng `translator` giả mà test adapter có thể gắn vào sys.modules.
    spec = importlib.util.spec_from_file_location("yinghua_xianxia_translator", TRANSLATOR_FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def engine() -> Any:
    if not TRANSLATOR_FILE.exists() or not all((DICT_DIR / name).exists() for name in DICT_FILES):
        pytest.skip("Không có module ảnh hoặc thư mục từ điển tu tiên")
    module: Any = _load_translator_module()
    module.NAMES_FILE = DICT_DIR / "Names.txt"
    module.VIETPHRASE_FILE = DICT_DIR / "VietPhrase.txt"
    module.LUATNHAN_FILE = DICT_DIR / "LuatNhan.txt"
    module.PHIENAM_FILE = DICT_DIR / "PhienAm.txt"
    return module.TranslationEngine()


def _translate(engine: Any, text: str) -> str:
    result: dict[str, str] = engine.translate(text)
    return result["vi"]


def test_split_letters_regex_detects_spaced_out_word() -> None:
    assert SPLIT_LETTERS_RE.search("hiện t r ê n n g ư ờ i cần")
    assert not SPLIT_LETTERS_RE.search("hiện trên người cần, 1 + 1 . . .")


@pytest.mark.parametrize(
    ("zh", "expected_vi"),
    [
        (
            "现在要靠自己打通身上干涸的隐形经脉永......",
            "hiện tại cần nhờ mình đả thông trên thân khô cạn đích ẩn hình kinh mạch vĩnh . . . . . .",
        ),
        ("你跟谁说话呢？！", "ngươi nói với ai đây？！"),
        (
            "把天晶沙当做杂质，采用淬炼精去除掉就可以了。",
            "coi Thiên Tinh cát là tạp chất， áp dụng rèn luyện tinh khứ trừ rơi là được rồi。",
        ),
        (
            "术炼师的天赋要求比武炼高的多，",
            "thuật luyện sư đích thiên phú yêu cầu cao hơn võ luyện nhiều，",
        ),
    ],
)
def test_luat_nhan_vietnamese_is_not_split_into_letters(engine: Any, zh: str, expected_vi: str) -> None:
    vi = _translate(engine, zh)
    assert not SPLIT_LETTERS_RE.search(vi), vi
    assert vi == expected_vi


@pytest.mark.parametrize(
    ("zh", "wrong_phrase"),
    [
        ("现在要靠自己打通身上干涸的隐形经脉永......", "hiện trên người cần"),
        ("你跟谁说话呢？！", "lời nói đâu"),
        ("把天晶沙当做杂质，采用淬炼精去除掉就可以了。", "là làm tạp chất"),
        ("术炼师的天赋要求比武炼高的多，", "đích nhiều"),
    ],
)
def test_luat_nhan_rule_does_not_swallow_neighbouring_words(engine: Any, zh: str, wrong_phrase: str) -> None:
    """Luật nhân không ăn mất "在" của 现在, không bỏ sót 话/做/的多 sau cụm khớp."""
    assert wrong_phrase not in _translate(engine, zh)


@pytest.mark.parametrize(
    ("zh", "expected_phrase"),
    [
        ("钥匙在他身上", "trên người"),
        ("一道光出现在他身上", "trên người"),
        ("我跟他说过了", "nói với"),
        ("别把我当傻子", "coi"),
        ("他比我高", "cao hơn"),
    ],
)
def test_luat_nhan_rule_still_applies_to_genuine_structure(
    engine: Any, zh: str, expected_phrase: str
) -> None:
    assert expected_phrase in _translate(engine, zh)


def test_latin_and_digit_runs_in_source_stay_together(engine: Any) -> None:
    vi = _translate(engine, "现在是天武历1033年。")
    assert "1033" in vi
    assert not SPLIT_LETTERS_RE.search(_translate(engine, "色彩助手：JXHFN责编：春雨"))


@pytest.mark.parametrize(
    ("zh", "expected_vi"),
    [
        ("一阶术炼师。", "nhất giai thuật luyện sư。"),
        ("我看看是什么方子～", "ta xem một chút là cái gì đơn thuốc ～"),
        (
            "我现在的身躯经脉尽数干涸，只要先找杨迪打通了经脉",
            "ta hiện tại đích thân thể kinh mạch đều khô cạn， "
            "chỉ cần trước tìm dương địch đả thông kinh mạch",
        ),
    ],
)
def test_standard_sentences_keep_previous_translation(engine: Any, zh: str, expected_vi: str) -> None:
    assert _translate(engine, zh) == expected_vi
