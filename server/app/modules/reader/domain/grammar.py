"""Phân tích ngữ pháp câu thoại (F05.09, US-NH-78): thực thể và phần kiểm tra thuần của kết quả do LLM trả về.

Không tin dữ liệu LLM: mọi trường đều được kiểm. Quy tắc theo docs/modules-functions.md F05.09 bước 5:
(a) đúng lược đồ; (b) các đoạn chữ ở nút lá ghép lại đúng bằng câu gốc (bỏ dấu câu và khoảng trắng khi so);
(c) nhãn thuộc danh sách cho phép; (d) ví dụ của mỗi điểm ngữ pháp chứa chính cấu trúc đó.
Cây sai thì bỏ cả cây; điểm ngữ pháp sai thì chỉ bỏ điểm đó.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any

# Nhãn thành phần câu (khóa tiếng Anh dùng trong JSON/CSDL) và tên hiển thị tiếng Việt.
LABELS: dict[str, str] = {
    "subject": "chủ ngữ",
    "predicate": "vị ngữ",
    "object": "tân ngữ",
    "complement": "bổ ngữ",
    "adverbial": "trạng ngữ",
    "attributive": "định ngữ",
    "particle": "trợ từ",
    "preposition": "giới từ",
    "conjunction": "liên từ",
    "measure": "lượng từ",
    "other": "khác",
}

MAX_SENTENCE_CHARS = 200
MAX_TREE_DEPTH = 4
MAX_TREE_NODES = 40
MAX_NODE_TEXT_CHARS = 100
MAX_NOTE_CHARS = 160
MAX_POINTS = 3
MAX_PATTERN_CHARS = 60
MAX_NAME_CHARS = 80
MAX_EXPLANATION_CHARS = 400
MAX_EXAMPLE_CHARS = 60
MAX_TRANSLATION_CHARS = 200
EXAMPLE_MAX_HSK_LEVEL = 4  # kết quả dùng chung mọi người nên chặn độ khó cố định, không theo trình độ riêng

# Từ chỉ loại thành phần LLM hay viết bằng chữ Hán trong công thức ("把 + 宾语 + 动词"): không phải chữ cố
# định
# của cấu trúc nên không đòi hỏi xuất hiện trong ví dụ.
_PLACEHOLDERS = re.compile(
    "主语|谓语|宾语|补语|状语|定语|动词|名词|形容词|副词|代词|量词|数词|助词|介词|连词|短语|句子|成分|处所|场所|对象|地点|时间"
)
_SEGMENT = re.compile(r"[㐀-䶿一-鿿]+(?:/[㐀-䶿一-鿿]+)*")
_PLACEHOLDER_LATIN = re.compile(r"[A-Za-z_]")
_HAN_RUN = re.compile(r"[㐀-䶿一-鿿\U00020000-\U0002fa1f]+")


class GrammarStatus(str, Enum):
    OK = "ok"
    UNAVAILABLE = "unavailable"  # LLM tắt, lỗi hoặc quá thời gian
    LIMIT_REACHED = "limit_reached"  # hết hạn mức phân tích trong ngày
    UNANALYZABLE = "unanalyzable"  # LLM trả về nhưng không còn phần nào hợp lệ


@dataclass(frozen=True, slots=True)
class SyntaxNode:
    label: str
    text: str
    note: str | None = None
    children: tuple[SyntaxNode, ...] = ()


@dataclass(frozen=True, slots=True)
class GrammarPoint:
    pattern: str  # cấu trúc bằng chữ Hán, vd. "把 + 宾语 + 动词"
    name: str  # tên cấu trúc tiếng Việt
    explanation: str
    example_zh: str
    example_vi: str


@dataclass(frozen=True, slots=True)
class GrammarContent:
    tree: tuple[
        SyntaxNode, ...
    ]  # các thành phần ở tầng ngoài cùng, theo thứ tự trong câu; rỗng nếu cây bị loại
    points: tuple[GrammarPoint, ...]

    @property
    def is_empty(self) -> bool:
        return not self.tree and not self.points


@dataclass(frozen=True, slots=True)
class GrammarAnalysis:
    id: int
    sentence_zh: str
    content: GrammarContent
    model: str | None


def normalize_sentence(text: str) -> str:
    """Unicode NFC, gộp mọi khoảng trắng liên tiếp (kể cả xuống dòng giữa các dòng chữ) thành một dấu cách."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def sentence_hash(sentence: str) -> str:
    """SHA-256 (hex, 64 ký tự) của câu đã chuẩn hóa — khóa cache dùng chung."""
    return hashlib.sha256(sentence.encode("utf-8")).hexdigest()


def han_runs(text: str) -> list[str]:
    return _HAN_RUN.findall(text)


def has_han(text: str) -> bool:
    return _HAN_RUN.search(text) is not None


def _core(text: str) -> str:
    """Chỉ giữ chữ và số (sau NFKC): bỏ dấu câu và khoảng trắng khi so khớp với câu gốc."""
    return "".join(c for c in unicodedata.normalize("NFKC", text) if unicodedata.category(c)[0] in "LN")


def _short_text(value: Any, max_chars: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text and len(text) <= max_chars else None


class _Budget:
    """Đếm số nút đã duyệt để chặn cây phình to."""

    def __init__(self) -> None:
        self.nodes = 0


def _parse_node(raw: Any, depth: int, budget: _Budget) -> tuple[SyntaxNode, str] | None:
    """(nút, chữ lõi của các lá bên dưới) hoặc None nếu nút/cây con sai."""
    budget.nodes += 1
    if not isinstance(raw, dict) or depth > MAX_TREE_DEPTH or budget.nodes > MAX_TREE_NODES:
        return None
    label, text = raw.get("label"), _short_text(raw.get("text"), MAX_NODE_TEXT_CHARS)
    if not isinstance(label, str) or label not in LABELS or text is None or not _core(text):
        return None
    raw_note = raw.get("note")
    note = _short_text(raw_note, MAX_NOTE_CHARS) if isinstance(raw_note, str) else None
    raw_children = raw.get("children") or []
    if not isinstance(raw_children, list):
        return None
    children: list[SyntaxNode] = []
    leaves = ""
    for raw_child in raw_children:
        parsed = _parse_node(raw_child, depth + 1, budget)
        if parsed is None:
            return None
        children.append(parsed[0])
        leaves += parsed[1]
    if not children:
        return SyntaxNode(label, text, note), _core(text)
    if leaves != _core(text):  # nút trong phải bằng đúng phần ghép của các nút con
        return None
    return SyntaxNode(label, text, note, tuple(children)), leaves


def parse_tree(raw_tree: object, sentence: str) -> tuple[SyntaxNode, ...]:
    """Cây cú pháp hợp lệ, hoặc `()` nếu sai bất kỳ chỗ nào (cả cây bị bỏ)."""
    if not isinstance(raw_tree, list) or not raw_tree:
        return ()
    budget = _Budget()
    nodes: list[SyntaxNode] = []
    leaves = ""
    for raw in raw_tree:
        parsed = _parse_node(raw, 1, budget)
        if parsed is None:
            return ()
        nodes.append(parsed[0])
        leaves += parsed[1]
    return tuple(nodes) if leaves == _core(sentence) else ()


def example_has_pattern(pattern: str, example_zh: str) -> bool:
    """Ví dụ chứa cấu trúc: mọi cụm chữ Hán cố định của `pattern` (bỏ từ chỉ loại thành phần) xuất hiện
    trong ví dụ theo đúng thứ tự. Cụm dạng "在/到" là lựa chọn: chỉ cần một trong hai xuất hiện."""
    segments = _SEGMENT.findall(_PLACEHOLDERS.sub(" ", pattern))
    if not segments:
        return False
    text = "".join(example_zh.split())  # LLM đôi khi chèn dấu cách giữa các từ của câu ví dụ
    position = 0
    for segment in segments:
        hits = [(found, len(alt)) for alt in segment.split("/") if (found := text.find(alt, position)) >= 0]
        if not hits:
            return False
        found, length = min(hits)
        position = found + length
    return True


def parse_points(raw_points: object) -> list[GrammarPoint]:
    """Điểm ngữ pháp đúng lược đồ và có ví dụ chứa cấu trúc; điểm sai bị bỏ. Chưa kiểm độ khó của ví dụ."""
    if not isinstance(raw_points, list):
        return []
    points: list[GrammarPoint] = []
    for raw in raw_points:
        point = _parse_point(raw)
        if point is not None and all(point.pattern != p.pattern for p in points):
            points.append(point)
    return points[:MAX_POINTS]


def _parse_point(raw: Any) -> GrammarPoint | None:
    if not isinstance(raw, dict):
        return None
    pattern = _short_text(raw.get("pattern"), MAX_PATTERN_CHARS)
    name = _short_text(raw.get("name"), MAX_NAME_CHARS)
    explanation = _short_text(raw.get("explanation"), MAX_EXPLANATION_CHARS)
    example_zh = _short_text(raw.get("example_zh"), MAX_EXAMPLE_CHARS)
    example_vi = _short_text(raw.get("example_vi"), MAX_EXPLANATION_CHARS)
    if pattern is None or name is None or explanation is None or example_zh is None or example_vi is None:
        return None
    if _PLACEHOLDER_LATIN.search(example_zh) or not example_has_pattern(pattern, example_zh):
        return None  # ví dụ còn ký hiệu giữ chỗ kiểu "N_A" là câu chưa hoàn chỉnh
    return GrammarPoint(pattern, name, explanation, example_zh, example_vi)


def content_to_json(content: GrammarContent) -> dict[str, Any]:
    return {
        "tree": [_node_to_json(n) for n in content.tree],
        "points": [
            {
                "pattern": p.pattern,
                "name": p.name,
                "explanation": p.explanation,
                "example_zh": p.example_zh,
                "example_vi": p.example_vi,
            }
            for p in content.points
        ],
    }


def _node_to_json(node: SyntaxNode) -> dict[str, Any]:
    return {
        "label": node.label,
        "text": node.text,
        "note": node.note,
        "children": [_node_to_json(c) for c in node.children],
    }


def content_from_json(data: object) -> GrammarContent | None:
    """Đọc lại nội dung đã lưu; dữ liệu hỏng trả None (người gọi coi như chưa có cache)."""
    if not isinstance(data, dict):
        return None
    try:
        tree = tuple(_node_from_json(n) for n in data.get("tree") or [])
        points = tuple(
            GrammarPoint(p["pattern"], p["name"], p["explanation"], p["example_zh"], p["example_vi"])
            for p in data.get("points") or []
        )
    except (KeyError, TypeError, AttributeError):
        return None
    return GrammarContent(tree, points)


def _node_from_json(data: dict[str, Any]) -> SyntaxNode:
    return SyntaxNode(
        data["label"],
        data["text"],
        data.get("note"),
        tuple(_node_from_json(c) for c in data.get("children") or []),
    )
