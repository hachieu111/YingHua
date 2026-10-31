"""Khai báo nhẹ (chỉ cột cần dùng) của bảng thuộc module khác, dành cho truy vấn của M17.

Dùng `sqlalchemy.table` thay vì import ORM model của module khác để không phụ thuộc hạ tầng của họ
(system-design.md); đổi tên cột ở module chủ sở hữu thì test sẽ báo ngay.
"""

from __future__ import annotations

from sqlalchemy import column, table

users = table("users", column("id"), column("status"))
series = table(
    "series", column("id"), column("title_vi"), column("visibility"), column("owner_id"), column("is_vip")
)
chapters = table("chapters", column("id"), column("series_id"), column("is_trial"))
