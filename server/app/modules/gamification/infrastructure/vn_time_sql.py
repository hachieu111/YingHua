"""Biểu thức SQL theo giờ Việt Nam. Tên múi giờ và đơn vị viết thẳng (literal) chứ không bind, để PostgreSQL
nhận ra cùng một biểu thức ở SELECT, GROUP BY và ORDER BY (tham số bind khác số thứ tự thì khác nhau)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Date, cast, func, literal_column

_ZONE: Any = literal_column("'Asia/Ho_Chi_Minh'")  # cùng độ lệch UTC+7 với VN_TZ của domain
_WEEK: Any = literal_column("'week'")


def vn_local(column: Any) -> Any:
    """timestamptz -> timestamp (giờ địa phương Việt Nam)."""
    return func.timezone(_ZONE, column)


def vn_date_of(column: Any) -> Any:
    return cast(vn_local(column), Date)


def vn_week_start(column: Any) -> Any:
    """timestamptz -> mốc Thứ Hai 00:00 giờ Việt Nam của tuần chứa nó, dạng timestamptz."""
    return func.timezone(_ZONE, func.date_trunc(_WEEK, vn_local(column)))
