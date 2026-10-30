"""
src/translator.py — Engine Dịch 4 Lớp (Phong Cách Tiên Hiệp)
=============================================================
Luồng dịch (sau khi YOLOv8 detect bubble + PP-OCR đọc chữ Hán):

  Lớp 1 — Names.txt:      Tra tên riêng (nhân vật, địa danh, kỹ năng tiên hiệp)
  Lớp 2 — VietPhrase.txt: Tra cụm từ thành ngữ (greedy — cụm dài ưu tiên)
  Lớp 3 — LuatNhan.txt:   Áp dụng luật regex (cấu trúc câu, so sánh, chương hồi)
  Lớp 4 — PhienAm.txt:    Phiên âm Hán-Việt cho từng chữ còn lại chưa tra được

  Pinyin: Dùng thư viện `pypinyin` (chuẩn, có dấu: nǐ hǎo)
          Fallback về PhienAm.txt nếu chưa cài pypinyin

Output: {"vi": str, "pinyin": str, "original": str, "method": str}
"""

import re
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ======================== ĐƯỜNG DẪN TỪ ĐIỂN ========================
_BASE    = Path(__file__).resolve().parent.parent.parent  # module xử lí ảnh

def _find_dict_file(filename: str) -> Path:
    candidates = [
        _BASE / "từ điển tu tiên" / filename,
        _BASE / "từ điển" / filename,
        Path(__file__).resolve().parent.parent / "từ điển tu tiên" / filename,
        Path(__file__).resolve().parent.parent / "từ điển" / filename,
        Path(r"D:\PTUD\từ điển tu tiên") / filename,
        Path(r"D:\PTUD\từ điển") / filename,
    ]
    for c in candidates:
        if c.exists():
            return c
    return _BASE / "từ điển tu tiên" / filename

NAMES_FILE      = _find_dict_file("Names.txt")
VIETPHRASE_FILE = _find_dict_file("VietPhrase.txt")
LUATNHAN_FILE   = _find_dict_file("LuatNhan.txt")
PHIENAM_FILE    = _find_dict_file("PhienAm.txt")

# Một cụm Latin/số liền nhau (kể cả chữ Việt có dấu) — xem _greedy_translate
_LATIN_RUN_RE = re.compile(r'[0-9A-Za-z\u00C0-\u024F\u1E00-\u1EFF\u0300-\u036F]+')

# Regex nhận biết ký tự Hán còn sót
_CHINESE_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df]')


# ======================== LOAD TỪ ĐIỂN ========================

def _read_dict(path: Path) -> dict:
    """Đọc file từ điển dạng key=value, encoding UTF-8 BOM.
    Nếu value có nhiều nghĩa phân cách bởi '/', chỉ lấy nghĩa đầu tiên.
    """
    d = {}
    if not path.exists():
        logger.warning(f"Khong tim thay tu dien: {path}")
        return d
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip()
                if k and v:
                    # Nếu có nhiều nghĩa phân cách bởi '/', chỉ lấy nghĩa đầu tiên
                    first_meaning = v.split("/")[0].strip()
                    if first_meaning:
                        d[k] = first_meaning
    logger.info(f"Loaded {len(d):,} entries from {path.name}")
    return d


def _read_luat_nhan(path: Path) -> list:
    """
    Đọc LuatNhan.txt thành list[(compiled_pattern, replacement_str)].
    Format mỗi dòng: regex_pattern=template_thay_thế  (với $1 $2... cho nhóm)
    """
    rules = []
    if not path.exists():
        logger.warning(f"Khong tim thay LuatNhan: {path}")
        return rules
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            pattern_str, _, replacement = line.partition("=")
            pattern_str = pattern_str.strip()
            replacement = replacement.strip()

            # Chuyển $1 $2 → \1 \2 cho Python re.sub
            repl = re.sub(r'\$(\d+)', r'\\\1', replacement)
            # Bỏ placeholder [CONVERT_NUMBER(\1)] → giữ lại nội dung nhóm \1
            repl = re.sub(r'\[CONVERT_NUMBER(?:_SPACED|_DIGITS)?\((.+?)\)\]', r'\1', repl)

            try:
                compiled = re.compile(pattern_str)
                rules.append((compiled, repl))
            except re.error as e:
                logger.debug(f"LuatNhan regex skip: {pattern_str!r} err={e}")

    logger.info(f"Loaded {len(rules)} rules from {path.name}")
    return rules


class TranslationEngine:
    """
    Engine dịch tiếng Trung → tiếng Việt phong cách tiên hiệp.
    Kết hợp 4 lớp từ điển + pypinyin.
    """

    def __init__(self):
        logger.info("Dang nap tu dien dich thuat...")

        self._names      = _read_dict(NAMES_FILE)
        self._vietphrase = _read_dict(VIETPHRASE_FILE)
        self._luat_nhan  = _read_luat_nhan(LUATNHAN_FILE)
        self._phienam    = _read_dict(PHIENAM_FILE)

        # Độ dài khóa dài nhất của mỗi từ điển: greedy match thử từ độ dài này giảm dần về 1 bằng tra dict
        # (O(độ dài câu × độ dài khóa)) thay vì duyệt cả triệu khóa ở mỗi vị trí như trước (chậm 0.5–1.5 s/câu).
        self._names_max_len = max(map(len, self._names), default=0)
        self._vp_max_len    = max(map(len, self._vietphrase), default=0)

        # Khởi tạo pypinyin
        self._pypinyin_ok = False
        try:
            from pypinyin import lazy_pinyin, Style
            self._lazy_pinyin   = lazy_pinyin
            self._pinyin_style  = Style
            self._pypinyin_ok   = True
            logger.info("pypinyin san sang")
        except ImportError:
            logger.warning("pypinyin chua cai. Dung PhienAm.txt lam Pinyin fallback.")

        logger.info("Tu dien san sang!")

    # -----------------------------------------------------------------
    #  PINYIN
    # -----------------------------------------------------------------
    def get_pinyin(self, text: str) -> str:
        """Lấy Pinyin chuẩn (có dấu tone) dùng pypinyin."""
        if self._pypinyin_ok:
            from pypinyin import lazy_pinyin, Style
            syllables = lazy_pinyin(text, style=Style.TONE)
            return " ".join(syllables)
        # Fallback: PhienAm.txt (Hán-Việt âm đọc)
        return " ".join(self._phienam.get(ch, ch) for ch in text)

    # -----------------------------------------------------------------
    #  LỚP 3: LuatNhan (áp dụng regex)
    # -----------------------------------------------------------------
    def _apply_luat_nhan(self, text: str) -> str:
        for pattern, repl in self._luat_nhan:
            try:
                new_text = pattern.sub(repl, text)
                if new_text != text:
                    text = new_text
            except Exception:
                pass
        return text

    # -----------------------------------------------------------------
    #  LỚP 1+2+4: Greedy match qua từng vị trí
    # -----------------------------------------------------------------
    @staticmethod
    def _longest_match(table: dict, max_len: int, text: str, i: int):
        """(nghĩa, độ dài) của khóa dài nhất trong `table` bắt đầu tại vị trí i; không có → None."""
        for length in range(min(max_len, len(text) - i), 0, -1):
            value = table.get(text[i:i + length])
            if value is not None:
                return value, length
        return None

    def _greedy_translate(self, text: str) -> str:
        """
        Duyệt chuỗi từ trái sang phải:
        1. Names (tên riêng — ưu tiên tuyệt đối)
        2. VietPhrase (cụm từ thành ngữ tiên hiệp)
        3. PhienAm (phiên âm 1 chữ còn lại)
        4. Giữ nguyên ký tự không tra được (dấu câu, số...)
        """
        result = []
        i = 0
        n = len(text)

        while i < n:
            # Lớp 1: Names (ưu tiên tuyệt đối), rồi Lớp 2: VietPhrase — mỗi lớp lấy khóa dài nhất khớp tại i
            hit = (self._longest_match(self._names, self._names_max_len, text, i)
                   or self._longest_match(self._vietphrase, self._vp_max_len, text, i))
            if hit:
                result.append(hit[0])
                i += hit[1]
                continue

            # Cụm Latin/số (chữ Việt do LuatNhan chèn, tên "JXHFN", số "1033") giữ nguyên cả cụm;
            # tách từng ký tự rồi nối bằng dấu cách sẽ ra "t r ê n n g ư ờ i".
            latin = _LATIN_RUN_RE.match(text, i)
            if latin:
                result.append(latin.group())
                i = latin.end()
                continue

            # Lớp 4: PhienAm (1 chữ)
            ch = text[i]
            result.append(self._phienam.get(ch, ch))
            i += 1

        return " ".join(r for r in result if r)

    # -----------------------------------------------------------------
    #  HÀM CHÍNH
    # -----------------------------------------------------------------
    def translate(self, text: str) -> dict:
        """
        Dịch 1 chuỗi chữ Hán → tiếng Việt phong cách tiên hiệp.

        Args:
            text: Chuỗi chữ Hán (đầu ra của PP-OCR từ bubble YOLO)

        Returns:
            {"original", "pinyin", "vi", "method"}
        """
        if not text or not text.strip():
            return {"original": text, "pinyin": "", "vi": "", "method": "empty"}

        original = text.strip()

        # 1. Pinyin (pypinyin, độc lập với bản dịch)
        pinyin = self.get_pinyin(original)

        # 2. LuatNhan regex (cấu trúc câu đặc biệt, ưu tiên cao)
        text_after_luat = self._apply_luat_nhan(original)

        # Nếu LuatNhan đã xử lý hoàn toàn (không còn chữ Hán)
        still_has_chinese = bool(_CHINESE_RE.search(text_after_luat))

        if not still_has_chinese:
            vi = text_after_luat.strip()
        else:
            # 3+4. Greedy translate (Names → VietPhrase → PhienAm)
            vi = self._greedy_translate(text_after_luat)

        # Dọn dẹp
        vi = re.sub(r'\s+', ' ', vi).strip()
        vi = re.sub(r'\s([,!?;:。，！？；：])', r'\1', vi)

        return {
            "original": original,
            "pinyin":   pinyin,
            "vi":       vi if vi else original,
            "method":   "4layer_xianxia",
        }

    def translate_batch(self, texts: list) -> list:
        """Dịch nhiều chuỗi cùng lúc."""
        return [self.translate(t) for t in texts]


# ======================== SINGLETON ========================
_engine_instance = None


def get_translator() -> TranslationEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = TranslationEngine()
    return _engine_instance
