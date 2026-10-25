"""Chữ và từ Hán rất phổ biến, dùng chung cho M09 (cầu nối từ mở rộng) và M10 (loại từ cơ bản khỏi gợi ý)."""

from __future__ import annotations

COMMON_CHARS = frozenset(
    "一不的是了人我你他她在有这那个大小上下中子么们来去说会要就也和都好多没着过到得地吗呢吧啊很还把被给让什能可为对以"
)


def is_common_char(char: str) -> bool:
    """Chữ Hán rất phổ biến (đại từ, hư từ, trợ từ, số một…)."""
    return char in COMMON_CHARS


# Từ quá cơ bản/hư từ không đáng gợi ý dù xuất hiện nhiều (F10.01); ngoài ra mọi từ chỉ gồm chữ phổ biến
# (什么, 我们, 不是…) cũng bị loại.
STOP_TERMS = frozenset(
    (
        "什么",
        "怎么",
        "怎样",
        "这个",
        "那个",
        "这些",
        "那些",
        "这里",
        "那里",
        "这样",
        "那样",
        "没有",
        "可以",
        "因为",
        "所以",
        "但是",
        "如果",
        "已经",
        "还是",
        "就是",
        "不是",
        "知道",
        "现在",
        "时候",
        "我们",
        "你们",
        "他们",
        "她们",
        "自己",
        "一个",
        "一下",
        "一些",
        "一起",
        "可是",
        "然后",
        "或者",
        "而且",
        "虽然",
        "只是",
        "还有",
        "不要",
    )
)


def is_stop_term(term: str) -> bool:
    """Hư từ hoặc từ chỉ gồm chữ rất phổ biến: không gợi ý học."""
    return term in STOP_TERMS or all(is_common_char(c) for c in term)
