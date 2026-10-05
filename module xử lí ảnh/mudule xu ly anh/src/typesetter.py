"""
Module: typesetter.py
Mục tiêu: Render chữ tiếng Việt vào bong bóng chat truyện tranh
          sao cho đúng phông chữ, tự động xuống dòng, căn giữa đẹp

Chiến lược font:
  - Dùng Source Han Sans (思源黑体) — hỗ trợ CẢ Trung lẫn Việt
  - Cùng 1 font family → phong cách đồng nhất, không "chớt quớt"
  - Có viền đen quanh chữ trắng (stroke) — chuẩn style Manhua
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import textwrap
import urllib.request
from pathlib import Path

# ===================================================
# FONT MANAGER — Tự động tải font nếu chưa có
# ===================================================

FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")

# Source Han Sans Bold — hỗ trợ Trung + Việt, phong cách Manhua
# Download từ GitHub của Adobe/Google (free, open source)
FONTS = {
    "main": {
        "filename": "SourceHanSansSC-Bold.otf",
        # Font chính: đậm, rõ ràng — dùng cho lời thoại
        "url": "https://github.com/adobe-fonts/source-han-sans/raw/release/OTF/SimplifiedChinese/SourceHanSansSC-Bold.otf",
        "fallback_url": "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansSC-Bold.otf"
    },
    "regular": {
        "filename": "SourceHanSansSC-Regular.otf",
        "url": "https://github.com/adobe-fonts/source-han-sans/raw/release/OTF/SimplifiedChinese/SourceHanSansSC-Regular.otf",
        "fallback_url": "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansSC-Regular.otf"
    }
}

# Fallback: Font có sẵn trên Windows hỗ trợ tiếng Việt tốt
WINDOWS_FALLBACK_FONTS = [
    r"C:\Windows\Fonts\msyh.ttc",       # Microsoft YaHei — có tiếng Trung + Việt
    r"C:\Windows\Fonts\msyhbd.ttc",     # Microsoft YaHei Bold
    r"C:\Windows\Fonts\msjh.ttc",       # Microsoft JhengHei
    r"C:\Windows\Fonts\arial.ttf",      # Fallback cuối cùng
]


def ensure_font_dir():
    Path(FONT_DIR).mkdir(parents=True, exist_ok=True)


def get_font_path(font_key: str = "main") -> str:
    """
    Lấy đường dẫn font — ưu tiên Source Han Sans,
    fallback về Microsoft YaHei (có sẵn trên Windows).
    """
    ensure_font_dir()
    font_info = FONTS.get(font_key, FONTS["main"])
    local_path = os.path.join(FONT_DIR, font_info["filename"])

    # Đã có font rồi
    if os.path.exists(local_path):
        return local_path

    # Thử tải từ internet
    print(f"  📥 Đang tải font {font_info['filename']}...")
    for url in [font_info["url"], font_info.get("fallback_url", "")]:
        if not url:
            continue
        try:
            urllib.request.urlretrieve(url, local_path)
            print(f"  ✅ Tải font thành công!")
            return local_path
        except Exception as e:
            print(f"  ⚠️  Tải thất bại ({url[:60]}...): {e}")

    # Fallback: dùng font Windows có sẵn
    print("  ⚠️  Không tải được font. Dùng font Windows có sẵn...")
    for win_font in WINDOWS_FALLBACK_FONTS:
        if os.path.exists(win_font):
            print(f"  ✅ Dùng font: {win_font}")
            return win_font

    raise FileNotFoundError(
        "Không tìm được font hỗ trợ tiếng Việt! "
        "Hãy đặt file font .ttf/.otf vào thư mục: " + FONT_DIR
    )


# ===================================================
# CORE TYPESETTING ENGINE
# ===================================================

class ComicTypesetter:
    """
    Engine tự động đặt chữ tiếng Việt vào bong bóng chat.
    
    Tính năng:
    - Tự động xuống dòng (word-wrap) cho tiếng Việt
    - Tự động scale font size vừa với bubble
    - Chữ trắng + viền đen (stroke) — đúng style Manhua
    - Căn giữa theo chiều ngang và dọc
    """

    def __init__(
        self,
        font_path: str = None,
        default_font_size: int = 28,
        text_color: tuple = (255, 255, 255),   # Trắng
        stroke_color: tuple = (0, 0, 0),        # Viền đen
        stroke_width: int = 2,
        min_font_size: int = 14,
        max_font_size: int = 60,
        padding: int = 8,                        # Khoảng cách lề trong bubble
    ):
        self.font_path = font_path or get_font_path("main")
        self.default_size = default_font_size
        self.text_color = text_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.min_size = min_font_size
        self.max_size = max_font_size
        self.padding = padding
        self._font_cache: dict[int, ImageFont.FreeTypeFont] = {}
        print(f"✅ Typesetter khởi tạo với font: {os.path.basename(self.font_path)}")

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Cache font theo size để tránh load lại nhiều lần."""
        if size not in self._font_cache:
            self._font_cache[size] = ImageFont.truetype(self.font_path, size)
        return self._font_cache[size]

    def _measure_text(self, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
        """Đo kích thước text (width, height) với font cho trước."""
        dummy_img = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
        """
        Word-wrap thông minh cho tiếng Việt.
        Tiếng Việt dùng khoảng trắng để phân tách từ — wrap theo từ.
        """
        words = text.split()
        if not words:
            return []

        lines = []
        current_line = ""

        for word in words:
            # Thử thêm từ vào dòng hiện tại
            test_line = (current_line + " " + word).strip()
            w, _ = self._measure_text(test_line, font)

            if w <= max_width:
                current_line = test_line
            else:
                # Dòng hiện tại đầy → xuống dòng mới
                if current_line:
                    lines.append(current_line)
                current_line = word

                # Nếu 1 từ đơn đã dài hơn max_width → vẫn thêm vào
                w_single, _ = self._measure_text(word, font)
                if w_single > max_width:
                    lines.append(current_line)
                    current_line = ""

        if current_line:
            lines.append(current_line)

        return lines

    def _find_optimal_font_size(
        self,
        text: str,
        bubble_w: int,
        bubble_h: int,
    ) -> tuple[int, list[str]]:
        """
        Tìm font size lớn nhất có thể vừa với bubble.
        Trả về (font_size, wrapped_lines)
        """
        inner_w = bubble_w - 2 * self.padding
        inner_h = bubble_h - 2 * self.padding

        best_size = self.min_size
        best_lines = [text]

        for size in range(self.max_size, self.min_size - 1, -1):
            font = self._get_font(size)
            lines = self._wrap_text(text, font, inner_w)
            if not lines:
                continue

            # Tính tổng chiều cao cần thiết
            line_h = size + 4  # line height = font size + spacing
            total_h = line_h * len(lines)

            # Kiểm tra có vừa bubble không
            max_line_w = max(self._measure_text(l, font)[0] for l in lines)

            if total_h <= inner_h and max_line_w <= inner_w:
                best_size = size
                best_lines = lines
                break  # Tìm được size tốt nhất

        return best_size, best_lines

    def _draw_text_with_stroke(
        self,
        draw: ImageDraw.Draw,
        x: int,
        y: int,
        text: str,
        font: ImageFont.FreeTypeFont,
    ):
        """
        Vẽ chữ có viền (stroke) — kỹ thuật chuẩn Manhua.
        Cách làm: vẽ viền trước (nhiều lớp offset), rồi vẽ chữ chính lên trên.
        """
        sw = self.stroke_width
        # Vẽ stroke (viền đen) bằng cách vẽ offset 8 hướng
        for dx in range(-sw, sw + 1):
            for dy in range(-sw, sw + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), text, font=font, fill=self.stroke_color)

        # Vẽ chữ chính lên trên
        draw.text((x, y), text, font=font, fill=self.text_color)

    def render_text_on_image(
        self,
        img_cv: np.ndarray,
        text_vi: str,
        bubble_x: int,
        bubble_y: int,
        bubble_w: int,
        bubble_h: int,
        bg_color: tuple = None,  # None = tự detect màu nền bubble
    ) -> np.ndarray:
        """
        Render chữ tiếng Việt vào vùng bubble trên ảnh.
        
        Args:
            img_cv:    Ảnh numpy BGR (đã qua inpainting — chữ Trung đã bị xóa)
            text_vi:   Bản dịch tiếng Việt cần render
            bubble_*:  Tọa độ và kích thước bubble
            bg_color:  Màu nền (tự detect nếu None)
        
        Returns:
            Ảnh đã có chữ Việt
        """
        if not text_vi or not text_vi.strip():
            return img_cv

        # Chuyển sang PIL để xử lý font (PIL xử lý Unicode tốt hơn OpenCV)
        img_pil = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)

        # Kích thước thực tế của bubble
        img_h, img_w = img_cv.shape[:2]
        bx = max(0, bubble_x)
        by = max(0, bubble_y)
        bw = min(bubble_w, img_w - bx)
        bh = min(bubble_h, img_h - by)

        # Tìm font size tối ưu + wrap text
        font_size, lines = self._find_optimal_font_size(text_vi, bw, bh)
        font = self._get_font(font_size)
        line_height = font_size + 5

        # Tính tổng chiều cao text block để căn giữa dọc
        total_text_h = line_height * len(lines)
        start_y = by + self.padding + (bh - 2 * self.padding - total_text_h) // 2

        # Vẽ từng dòng — căn giữa ngang
        for i, line in enumerate(lines):
            line_w, _ = self._measure_text(line, font)
            line_x = bx + self.padding + (bw - 2 * self.padding - line_w) // 2
            line_y = start_y + i * line_height

            self._draw_text_with_stroke(draw, line_x, line_y, line, font)

        # Chuyển lại BGR
        result = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        return result

    def render_preview(
        self,
        text_vi: str,
        bubble_w: int = 300,
        bubble_h: int = 150,
        bg_color: tuple = (255, 255, 255),
    ) -> np.ndarray:
        """
        Tạo ảnh preview xem trước chữ sẽ trông như thế nào.
        Dùng để test font và layout.
        """
        img = np.full((bubble_h, bubble_w, 3), bg_color, dtype=np.uint8)

        # Vẽ viền bubble để dễ nhìn
        cv2.rectangle(img, (2, 2), (bubble_w - 3, bubble_h - 3), (200, 200, 200), 2)

        return self.render_text_on_image(
            img, text_vi,
            bubble_x=0, bubble_y=0,
            bubble_w=bubble_w, bubble_h=bubble_h
        )


# ===================================================
# FONT SETUP HELPER — Chạy 1 lần để tải font
# ===================================================

def setup_fonts():
    """
    Hàm tiện ích để tải font về máy.
    Chạy lần đầu hoặc khi muốn cập nhật font.
    """
    print("=" * 50)
    print("🔤 Thiết lập Font cho Comic Typesetter")
    print("=" * 50)
    
    ensure_font_dir()
    
    # Thử tải Source Han Sans trước
    for key in ["main", "regular"]:
        try:
            path = get_font_path(key)
            print(f"✅ Font '{key}': {path}")
        except FileNotFoundError as e:
            print(f"❌ {e}")
    
    print("\n📁 Thư mục font:", FONT_DIR)
    print("\nNếu tải tự động thất bại, hãy:")
    print("  1. Tải Source Han Sans tại: https://github.com/adobe-fonts/source-han-sans/releases")
    print("  2. Đặt file SourceHanSansSC-Bold.otf vào:", FONT_DIR)
    print("  3. HOẶC dùng Microsoft YaHei có sẵn trên Windows (tự động fallback)")


# ===================================================
# SINGLETON
# ===================================================

_typesetter_instance: ComicTypesetter | None = None


def get_typesetter() -> ComicTypesetter:
    """Singleton — chỉ khởi tạo 1 lần."""
    global _typesetter_instance
    if _typesetter_instance is None:
        _typesetter_instance = ComicTypesetter()
    return _typesetter_instance


# ===================================================
# DEMO / TEST
# ===================================================

if __name__ == "__main__":
    print("🧪 Test Typesetter...")
    
    setup_fonts()
    ts = get_typesetter()
    
    test_cases = [
        {
            "text": "Cậu có biết không? Ta là người mạnh nhất trong thiên hạ này!",
            "w": 350, "h": 120,
            "bg": (245, 245, 245)
        },
        {
            "text": "Không được đi! Hãy nói cho ta biết phương pháp hóa giải!",
            "w": 280, "h": 100,
            "bg": (255, 255, 255)
        },
        {
            "text": "Ừ......",
            "w": 180, "h": 80,
            "bg": (255, 255, 255)
        },
        {
            "text": "Thân xác này mới 15 tuổi, nếu không nhanh chóng thanh lọc kinh mạch thì càng khó hồi phục đỉnh phong!",
            "w": 320, "h": 150,
            "bg": (250, 250, 250)
        },
    ]
    
    import cv2
    previews = []
    for i, case in enumerate(test_cases):
        preview = ts.render_preview(
            text_vi=case["text"],
            bubble_w=case["w"],
            bubble_h=case["h"],
            bg_color=case["bg"]
        )
        previews.append(preview)
        print(f"  Test {i+1}: '{case['text'][:30]}...' → OK")
    
    # Ghép các preview lại thành 1 ảnh để xem
    max_h = max(p.shape[0] for p in previews)
    padded = []
    for p in previews:
        pad = np.full((max_h, p.shape[1], 3), 200, dtype=np.uint8)
        pad[:p.shape[0], :p.shape[1]] = p
        padded.append(pad)
    
    # Thêm padding giữa các preview
    separator = np.full((max_h, 10, 3), 150, dtype=np.uint8)
    result = padded[0]
    for p in padded[1:]:
        result = np.hstack([result, separator, p])
    
    output_path = r"d:\PTUD\mudule xu ly anh\font_preview.jpg"
    cv2.imencode('.jpg', result)[1].tofile(output_path)
    print(f"\n✅ Đã lưu preview tại: {output_path}")
    print("Mở file đó để xem kết quả font rendering!")
