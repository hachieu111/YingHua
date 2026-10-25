"""Nhãn từ loại: mã của danh sách HSK (kiểu ICTCLAS) → tiếng Việt."""

from __future__ import annotations

_POS_VI = {
    "n": "danh từ",
    "nr": "tên người",
    "ns": "tên địa điểm",
    "nt": "tên tổ chức",
    "nz": "danh từ riêng",
    "vn": "danh động từ",
    "v": "động từ",
    "a": "tính từ",
    "an": "danh tính từ",
    "ad": "tính từ trạng ngữ",
    "d": "phó từ",
    "p": "giới từ",
    "m": "số từ",
    "q": "lượng từ",
    "r": "đại từ",
    "c": "liên từ",
    "u": "trợ từ",
    "y": "ngữ khí từ",
    "e": "thán từ",
    "o": "từ tượng thanh",
    "t": "từ chỉ thời gian",
    "s": "từ chỉ nơi chốn",
    "f": "từ chỉ phương vị",
    "b": "từ khu biệt",
    "z": "từ trạng thái",
    "i": "thành ngữ",
    "l": "quán ngữ",
    "j": "từ viết tắt",
    "g": "hình vị",
    "h": "tiền tố",
    "k": "hậu tố",
}


def pos_labels(raw: str | None) -> tuple[str, ...]:
    """'v,vn' → ('động từ', 'danh động từ'). Mã lạ được giữ nguyên để không mất thông tin."""
    if not raw:
        return ()
    labels: list[str] = []
    for code in (part.strip() for part in raw.split(",")):
        if not code:
            continue
        label = _POS_VI.get(code, code)
        if label not in labels:
            labels.append(label)
    return tuple(labels)
