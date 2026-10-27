"""Dựng phản hồi tải tệp cho F07.08."""

from __future__ import annotations

from fastapi import Response

from app.modules.vocab.domain.export import ExportFile


def export_response(file: ExportFile) -> Response:
    """Tên tệp do hệ thống tạo (ký tự an toàn) nên đưa thẳng vào Content-Disposition."""
    return Response(
        content=file.content,
        media_type=file.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file.filename}"',
            "X-Export-Count": str(file.row_count),
            "Cache-Control": "no-store",
        },
    )
