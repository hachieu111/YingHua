import os
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen

def inject_tilde_into_font(input_path: str, output_path: str):
    print(f"Processing: {input_path}")
    font = TTFont(input_path)
    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet()

    # Tìm chữ 'Ã' (0x00C3) hoặc 'ã' (0x00E3) trong font để lấy mẫu nét vẽ dấu '~' gốc
    source_code = 0x00C3 if 0x00C3 in cmap else 0x00E3
    if source_code not in cmap:
        print("  ❌ Không tìm thấy chữ Ã hoặc ã trong font này!")
        return

    source_glyph_name = cmap[source_code]

    # Ghi lại toàn bộ các đường cong vector (contours) của chữ 'Ã'
    rec_pen = RecordingPen()
    glyph_set[source_glyph_name].draw(rec_pen)

    # Tách các đường cong thành từng nét độc lập (chữ A ở dưới và dấu ~ ở trên đỉnh)
    contours = []
    current_contour = []
    for operator, operands in rec_pen.value:
        current_contour.append((operator, operands))
        if operator in ("closePath", "endPath"):
            contours.append(current_contour)
            current_contour = []

    def get_contour_bbox(contour):
        pts = [pt for op, args in contour for pt in args if isinstance(pt, tuple)]
        if not pts:
            return 0, 0, 0, 0
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)

    # Nét vẽ có tọa độ Y cao nhất chính là dấu '~' nằm trên đỉnh chữ 'Ã'
    # Lọc bỏ các contour không có điểm
    valid_contours = [c for c in contours if any(isinstance(pt, tuple) for op, args in c for pt in args)]
    if not valid_contours:
        print("  ❌ Chữ Ã rỗng!")
        return

    tilde_contour = max(valid_contours, key=lambda c: get_contour_bbox(c)[3])
    base_contours = [c for c in valid_contours if c is not tilde_contour]

    # Tính kích thước dấu '~' gốc và chiều cao thân chữ 'A'
    min_x, min_y, max_x, max_y = get_contour_bbox(tilde_contour)
    
    if base_contours:
        base_min_y = min(get_contour_bbox(c)[1] for c in base_contours)
        base_max_y = max(get_contour_bbox(c)[3] for c in base_contours)
        cap_height = base_max_y - base_min_y
    else:
        base_min_y = 0
        cap_height = 1000

    # Phóng to dấu '~' lên 1.35 lần và hạ từ đỉnh chữ A xuống chính giữa dòng
    scale = 1.35
    lsb = 60  # Khoảng cách lề trái/phải của ký tự ~
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    target_cy = base_min_y + cap_height * 0.48  # Đặt ở tầm giữa chữ IN HOA

    dx = lsb - (scale * min_x)
    dy = target_cy - (scale * cy)

    # Vẽ ký tự '~' độc lập vào bảng glyf
    tt_pen = TTGlyphPen(None)
    trans_pen = TransformPen(tt_pen, (scale, 0, 0, scale, dx, dy))
    for operator, operands in tilde_contour:
        getattr(trans_pen, operator)(*operands)

    new_glyph = tt_pen.glyph()
    new_glyph_name = "uni007E_tilde"

    # Thêm ký tự mới vào danh sách Glyph của Font
    glyph_order = font.getGlyphOrder()
    if new_glyph_name not in glyph_order:
        glyph_order.append(new_glyph_name)
        font.setGlyphOrder(glyph_order)

    font["glyf"][new_glyph_name] = new_glyph
    new_width = int((max_x - min_x) * scale) + (lsb * 2)
    font["hmtx"][new_glyph_name] = (new_width, lsb)

    # Gán ký tự vừa tạo cho TẤT CẢ các mã dấu ngã
    tilde_codepoints = [
        0x007E,  # ~ (ASCII Tilde)
        0xFF5E,  # ～ (Fullwidth Tilde)
        0x301C,  # 〜 (Wave Dash)
        0x02DC,  # ˜ (Small Tilde)
        0x223C   # ∼ (Tilde Operator)
    ]
    
    for table in font["cmap"].tables:
        if table.isUnicode():
            for code in tilde_codepoints:
                table.cmap[code] = new_glyph_name

    font.save(output_path)
    print(f"  ✅ Đã cấy thành công ký tự '~' vào file: {output_path}")


if __name__ == "__main__":
    base_dir = r"D:\PTUD\font chữ\Font-chu-truyen-tranh-Comic\Font chữ truyện tranh Comic\Font-HL-Comic"
    fonts_to_fix = ["HLcomic1_normal.ttf", "HLcomic3_bold.ttf", "HLcomic8_Italic.ttf"]
    
    for font_name in fonts_to_fix:
        input_path = os.path.join(base_dir, font_name)
        # Ghi đè trực tiếp lên file gốc hoặc lưu thành -Fixed
        output_path = os.path.join(base_dir, font_name) 
        inject_tilde_into_font(input_path, output_path)
