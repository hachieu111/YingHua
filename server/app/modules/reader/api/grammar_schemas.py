from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.reader.application.dto import GrammarView
from app.modules.reader.domain.grammar import LABELS, GrammarPoint, GrammarStatus, SyntaxNode

AI_LABEL = "Do AI phân tích, có thể chưa chính xác"
MESSAGES: dict[GrammarStatus, str] = {
    GrammarStatus.UNAVAILABLE: "Tạm thời chưa phân tích được câu này",
    GrammarStatus.LIMIT_REACHED: "Bạn đã dùng hết lượt phân tích ngữ pháp hôm nay. Hãy thử lại vào ngày mai",
    GrammarStatus.UNANALYZABLE: "Chưa phân tích được câu này",
}


class SyntaxNodeResponse(BaseModel):
    label: str = Field(description="Khóa nhãn: subject, predicate, object, complement, adverbial, ...")
    label_vi: str = Field(description="Tên nhãn tiếng Việt: chủ ngữ, vị ngữ, tân ngữ, ...")
    text: str
    note: str | None = Field(description="Giải thích ngắn của nhánh; giao diện hiện khi bấm vào nhánh")
    children: list[SyntaxNodeResponse]

    @classmethod
    def from_node(cls, node: SyntaxNode) -> SyntaxNodeResponse:
        return cls(
            label=node.label,
            label_vi=LABELS[node.label],
            text=node.text,
            note=node.note,
            children=[cls.from_node(c) for c in node.children],
        )


class GrammarPointResponse(BaseModel):
    pattern: str = Field(description="Cấu trúc bằng chữ Hán, vd. 把 + 宾语 + 动词")
    name: str
    explanation: str
    example_zh: str
    example_vi: str

    @classmethod
    def from_point(cls, p: GrammarPoint) -> GrammarPointResponse:
        return cls(
            pattern=p.pattern,
            name=p.name,
            explanation=p.explanation,
            example_zh=p.example_zh,
            example_vi=p.example_vi,
        )


class GrammarResponse(BaseModel):
    status: str = Field(description="ok | unavailable | limit_reached | unanalyzable")
    bubble_id: int
    sentence: str = Field(description="Câu đã chuẩn hóa (NFC, gộp khoảng trắng)")
    cached: bool = Field(description="True nếu lấy từ bộ nhớ dùng chung, không tốn hạn mức")
    message: str | None = Field(description="Thông báo nhẹ cho người học khi status khác ok")
    ai_label: str | None = Field(description="Nhãn nguồn AI; có khi status là ok")
    tree: list[SyntaxNodeResponse] = Field(description="Rỗng nếu cây bị loại hoặc không có kết quả")
    points: list[GrammarPointResponse]

    @classmethod
    def from_view(cls, view: GrammarView) -> GrammarResponse:
        content = view.content
        return cls(
            status=view.status.value,
            bubble_id=view.bubble_id,
            sentence=view.sentence,
            cached=view.cached,
            message=MESSAGES.get(view.status),
            ai_label=AI_LABEL if content is not None else None,
            tree=[SyntaxNodeResponse.from_node(n) for n in content.tree] if content else [],
            points=[GrammarPointResponse.from_point(p) for p in content.points] if content else [],
        )


SyntaxNodeResponse.model_rebuild()
