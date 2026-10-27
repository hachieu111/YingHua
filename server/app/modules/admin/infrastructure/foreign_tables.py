"""Khai báo nhẹ (chỉ tên cột cần dùng) của bảng thuộc module khác, dành cho truy vấn kiểm duyệt của M13.

Dùng `sqlalchemy.table` thay vì import ORM model của module khác để không phụ thuộc vào hạ tầng của họ
(system-design.md); cột đổi tên ở module chủ sở hữu thì test kiểm duyệt sẽ báo ngay.
"""

from __future__ import annotations

from sqlalchemy import column, table

stored_files = table(
    "stored_files",
    column("id"),
    column("kind"),
    column("sha256"),
    column("mime_type"),
    column("size_bytes"),
    column("width"),
    column("height"),
    column("owner_id"),
    column("removed_at"),
    column("created_at"),
)
pages = table(
    "pages",
    column("id"),
    column("chapter_id"),
    column("owner_id"),
    column("original_file_id"),
    column("translation_id"),
    column("page_no"),
)
chapters = table("chapters", column("id"), column("series_id"), column("number"), column("title"))
series = table("series", column("id"), column("visibility"), column("title_vi"))
translations = table(
    "translations",
    column("id"),
    column("status"),
    column("source_file_id"),
    column("inpainted_file_id"),
    column("rendered_file_id"),
)
bubbles = table("bubbles", column("id"), column("translation_id"), column("text_zh"))
vocab_contexts = table("vocab_contexts", column("page_id"), column("snippet_file_id"))
users = table("users", column("id"), column("display_name"), column("email"))
