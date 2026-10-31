"""Khai báo nhẹ (chỉ cột cần dùng) của bảng thuộc module khác, dành cho truy vấn của M16.

Dùng `sqlalchemy.table` thay vì import ORM model của module khác để không phụ thuộc hạ tầng của họ
(system-design.md); đổi tên cột ở module chủ sở hữu thì test sẽ báo ngay.
"""

from __future__ import annotations

from sqlalchemy import column, table

users = table(
    "users",
    column("id"),
    column("display_name"),
    column("avatar_file_id"),
    column("avatar_preset"),
    column("status"),
    column("created_at"),
)
user_settings = table(
    "user_settings",
    column("user_id"),
    column("timezone"),
    column("weekly_page_goal"),
    column("hsk_level"),
    column("show_on_leaderboard"),
)
daily_activities = table(
    "daily_activities",
    column("user_id"),
    column("activity_date"),
    column("reviews_count"),
    column("pages_read"),
    column("words_saved"),
    column("updated_at"),
)
page_reads = table("page_reads", column("user_id"), column("page_id"), column("first_read_at"))
vocab_entries = table(
    "vocab_entries", column("id"), column("user_id"), column("term"), column("hsk_level"), column("status")
)
cards = table("cards", column("id"), column("vocab_entry_id"), column("state"), column("stability"))
review_logs = table(
    "review_logs", column("user_id"), column("card_id"), column("rating"), column("reviewed_at")
)
hanzi = table("hanzi", column("ch"), column("pinyin"), column("radical"), column("components"))
hsk_words = table("hsk_words", column("word"), column("level"))
lookup_events = table(
    "lookup_events", column("user_id"), column("bubble_id"), column("action"), column("created_at")
)
