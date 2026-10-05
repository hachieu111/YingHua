"""
label_tool.py — Desktop GUI gán nhãn truyện tranh (Tkinter)
=============================================================
Phiên bản nâng cấp:
  - Gán nhãn đa lớp: speech_bubble | sound_effect | calligraphy
  - Màu sắc riêng cho từng class
  - Semi-supervised: AI tự đề xuất box + text
  - Export YOLO polygon dataset
"""

import os
import glob
import json
import shutil
import cv2
import numpy as np
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
from PIL import Image, ImageTk, ImageDraw
from pathlib import Path

try:
    from paddleocr import PaddleOCR
    _HAS_OCR = True
except ImportError:
    _HAS_OCR = False

IMG_DIR    = r"d:\tool ghép ảnh\ket_qua_ghep_anh\chap02"
LABEL_FILE = r"d:\PTUD\mudule xu ly anh\labels.txt"
EXPORT_DIR = r"d:\PTUD\mudule xu ly anh\dataset\yolo_export"

# ==================== CLASS DEFINITIONS ====================
CLASSES = [
    {"id": 0, "name": "speech_bubble", "label": "💬 Bong bóng chat",       "color": "#e84118", "tk_color": "red"},
    {"id": 1, "name": "sound_effect",  "label": "💥 Âm thanh / SFX",       "color": "#e67e22", "tk_color": "orange"},
    {"id": 2, "name": "calligraphy",   "label": "✍️ Thư pháp / Chiêu thức", "color": "#8e44ad", "tk_color": "purple"},
]
FLOATING_COLOR = "#f1c40f"  # Màu hiển thị floating text


class ComicLabeler:
    def __init__(self, master):
        self.master = master
        self.master.title("🎌 Comic Label Tool v2 — Multi-Class")

        # State
        self.image_paths   = []
        self.current_idx   = 0
        self.boxes         = []          # [{box, text, class_id, polygon, id, text_id, cls_id_lbl}]
        self.scale         = 1.0
        self.all_labels    = {}
        self.active_class  = 0           # class đang vẽ
        self.start_x       = None
        self.start_y       = None
        self.rect          = None        # preview rect khi drag

        # Load OCR
        self.ocr = None
        if _HAS_OCR:
            print("Đang khởi tạo AI Model (PP-OCR)...")
            self.ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
            print("Khởi tạo hoàn tất!")
        else:
            print("⚠️ PaddleOCR chưa cài, không có tính năng AI auto-predict.")

        # Load ảnh
        self.image_paths = [
            p for p in glob.glob(os.path.join(IMG_DIR, "*.*"))
            if p.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        self.image_paths.sort()

        self.setup_ui()
        self.load_labels_from_file()

        if self.image_paths:
            self.load_image()
        else:
            messagebox.showwarning(
                "Cảnh báo",
                f"Không tìm thấy file ảnh nào trong thư mục:\n{IMG_DIR}"
            )

    # ------------------------------------------------------------------ #
    #  UI SETUP                                                            #
    # ------------------------------------------------------------------ #
    def setup_ui(self):
        self.master.configure(bg="#0e1117")

        # ---- Top toolbar ----
        toolbar = tk.Frame(self.master, bg="#1a1f35", pady=8)
        toolbar.pack(fill=tk.X)

        tk.Button(
            toolbar, text="◀ Trở lại", command=self.prev_img,
            font=("Segoe UI", 10, "bold"), bg="#334155", fg="white",
            relief=tk.FLAT, padx=10, pady=4
        ).pack(side=tk.LEFT, padx=6)

        self.lbl_info = tk.Label(
            toolbar, text="Ảnh: 0/0", fg="#94a3b8", bg="#1a1f35",
            font=("Segoe UI", 11)
        )
        self.lbl_info.pack(side=tk.LEFT, padx=12)

        tk.Button(
            toolbar, text="💾 Lưu & Tiếp ▶", command=self.save_and_next,
            font=("Segoe UI", 10, "bold"), bg="#22c55e", fg="white",
            relief=tk.FLAT, padx=10, pady=4
        ).pack(side=tk.LEFT, padx=6)

        if self.ocr:
            tk.Button(
                toolbar, text="🤖 AI Pseudo-label", command=self.auto_predict,
                font=("Segoe UI", 10, "bold"), bg="#3b82f6", fg="white",
                relief=tk.FLAT, padx=10, pady=4
            ).pack(side=tk.LEFT, padx=6)

        tk.Button(
            toolbar, text="📦 Export YOLO", command=self.export_yolo,
            font=("Segoe UI", 10, "bold"), bg="#8b5cf6", fg="white",
            relief=tk.FLAT, padx=10, pady=4
        ).pack(side=tk.LEFT, padx=6)

        tk.Label(
            toolbar,
            text="Kéo ảnh = Vẽ box | Kéo box = Di chuyển | Đúp = Sửa/Xóa",
            fg="#475569", bg="#1a1f35", font=("Segoe UI", 9)
        ).pack(side=tk.RIGHT, padx=16)

        # ---- Class selector bar ----
        cls_bar = tk.Frame(self.master, bg="#111827", pady=6)
        cls_bar.pack(fill=tk.X)

        tk.Label(
            cls_bar, text="  Loại nhãn đang vẽ:",
            fg="#64748b", bg="#111827", font=("Segoe UI", 9)
        ).pack(side=tk.LEFT)

        self.class_btns = []
        for cls in CLASSES:
            btn = tk.Button(
                cls_bar,
                text=cls["label"],
                command=lambda cid=cls["id"]: self.set_active_class(cid),
                font=("Segoe UI", 9, "bold"),
                bg=cls["tk_color"], fg="white",
                relief=tk.FLAT, padx=8, pady=3,
                bd=2
            )
            btn.pack(side=tk.LEFT, padx=4)
            self.class_btns.append(btn)

        # Shortcut keys hint
        tk.Label(
            cls_bar, text="  [1] Bong bóng  [2] Âm thanh  [3] Thư pháp",
            fg="#475569", bg="#111827", font=("Segoe UI", 8)
        ).pack(side=tk.RIGHT, padx=12)

        # ---- Main area: canvas + sidebar ----
        main_frame = tk.Frame(self.master, bg="#0e1117")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas
        self.canvas = tk.Canvas(main_frame, cursor="cross", bg="#080c14", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas.bind("<ButtonPress-1>",   self.on_press)
        self.canvas.bind("<B1-Motion>",        self.on_drag)
        self.canvas.bind("<ButtonRelease-1>",  self.on_release)
        self.canvas.bind("<Double-Button-1>",  self.on_double_click)

        # Keyboard shortcuts
        self.master.bind("1", lambda e: self.set_active_class(0))
        self.master.bind("2", lambda e: self.set_active_class(1))
        self.master.bind("3", lambda e: self.set_active_class(2))
        self.master.bind("<Right>", lambda e: self.save_and_next())
        self.master.bind("<Left>",  lambda e: self.prev_img())

        # Sidebar
        sidebar = tk.Frame(main_frame, bg="#111827", width=260)
        sidebar.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar, text="📋 DANH SÁCH NHÃN",
            fg="#475569", bg="#111827",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor=tk.W, padx=12, pady=(12, 4))

        # Listbox nhãn
        self.listbox_frame = tk.Frame(sidebar, bg="#111827")
        self.listbox_frame.pack(fill=tk.BOTH, expand=True, padx=8)

        scrollbar = tk.Scrollbar(self.listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(
            self.listbox_frame,
            bg="#1e293b", fg="#cbd5e1",
            font=("Consolas", 9),
            selectbackground="#334155",
            relief=tk.FLAT, bd=0,
            yscrollcommand=scrollbar.set
        )
        self.listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)
        self.listbox.bind("<Double-Button-1>", lambda e: self._listbox_double())

        # Stats
        self.stats_var = tk.StringVar(value="")
        tk.Label(
            sidebar, textvariable=self.stats_var,
            fg="#64748b", bg="#111827",
            font=("Segoe UI", 9), justify=tk.LEFT, anchor=tk.W
        ).pack(anchor=tk.W, padx=12, pady=8)

        # Highlight active class ban đầu
        self.set_active_class(0)

    def set_active_class(self, class_id: int):
        self.active_class = class_id
        for btn in self.class_btns:
            btn.configure(relief=tk.FLAT)
        if class_id < len(self.class_btns):
            self.class_btns[class_id].configure(relief=tk.SUNKEN)

    # ------------------------------------------------------------------ #
    #  LABEL I/O                                                           #
    # ------------------------------------------------------------------ #
    def load_labels_from_file(self):
        if os.path.exists(LABEL_FILE):
            with open(LABEL_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) == 2:
                        self.all_labels[parts[0]] = json.loads(parts[1])

    def save_labels(self):
        os.makedirs(os.path.dirname(LABEL_FILE), exist_ok=True)
        with open(LABEL_FILE, 'w', encoding='utf-8') as f:
            for path, data in self.all_labels.items():
                f.write(f"{path}\t{json.dumps(data, ensure_ascii=False)}\n")

    # ------------------------------------------------------------------ #
    #  IMAGE LOAD & DISPLAY                                                #
    # ------------------------------------------------------------------ #
    def load_image(self):
        self.canvas.delete("all")
        self.boxes = []

        path = self.image_paths[self.current_idx]
        self.lbl_info.config(
            text=f"Ảnh: {self.current_idx + 1}/{len(self.image_paths)} — {os.path.basename(path)}"
        )

        img_cv = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img_cv is None:
            return
        self.original_img = img_cv

        h, w = img_cv.shape[:2]
        max_h = 800
        if h > max_h:
            self.scale = max_h / h
            new_w = int(w * self.scale)
            new_h = max_h
            img_resized = cv2.resize(img_cv, (new_w, new_h))
        else:
            self.scale = 1.0
            img_resized = img_cv

        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        self.tk_img = ImageTk.PhotoImage(Image.fromarray(img_rgb))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)

        # Load nhãn hoặc AI predict
        if path in self.all_labels:
            for item in self.all_labels[path]:
                self.draw_box(
                    item['box'],
                    item['text'],
                    item.get('class_id', 0),
                    item.get('polygon', None)
                )
        elif self.ocr:
            self.auto_predict()

        self.update_sidebar()

    def draw_box(self, box, text, class_id=0, polygon=None):
        """Vẽ bbox lên canvas với màu theo class."""
        cls = CLASSES[class_id] if class_id < len(CLASSES) else CLASSES[0]
        color = cls["tk_color"]

        x, y, w, h = box
        sx, sy = x * self.scale, y * self.scale
        sw, sh = w * self.scale, h * self.scale

        rect_id = self.canvas.create_rectangle(
            sx, sy, sx + sw, sy + sh,
            outline=color, width=2
        )
        # Class label tag
        cls_lbl_id = self.canvas.create_text(
            sx + 2, sy + 2,
            text=cls["label"], fill=color,
            anchor=tk.NW, font=("Segoe UI", 8, "bold")
        )
        # Text content
        text_id = self.canvas.create_text(
            sx, sy - 14, text=text if text else "(trống)",
            fill="white", anchor=tk.NW, font=("Consolas", 11, "bold")
        )
        self.boxes.append({
            "box": box, "text": text,
            "class_id": class_id,
            "polygon": polygon,
            "id": rect_id,
            "text_id": text_id,
            "cls_id_lbl": cls_lbl_id
        })

    def update_sidebar(self):
        self.listbox.delete(0, tk.END)
        counts = {cls["name"]: 0 for cls in CLASSES}
        for b in self.boxes:
            cls = CLASSES[b["class_id"]] if b["class_id"] < len(CLASSES) else CLASSES[0]
            self.listbox.insert(
                tk.END,
                f"[{cls['label']}] {b['text'] or '(trống)'}"
            )
            self.listbox.itemconfig(
                tk.END, fg=cls["color"] if hasattr(cls, "color") else "white"
            )
            counts[cls["name"]] += 1

        stats_lines = ["📊 Thống kê:"]
        for cls in CLASSES:
            stats_lines.append(f"  {cls['label']}: {counts[cls['name']]}")
        stats_lines.append(f"  Tổng: {len(self.boxes)}")
        self.stats_var.set("\n".join(stats_lines))

    def _listbox_double(self):
        sel = self.listbox.curselection()
        if sel:
            self.on_double_click_box(sel[0])

    # ------------------------------------------------------------------ #
    #  MOUSE EVENTS                                                        #
    # ------------------------------------------------------------------ #
    def on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        cls = CLASSES[self.active_class]
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline=cls["tk_color"], width=2, dash=(4, 2)
        )

    def on_drag(self, event):
        if self.rect:
            self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        end_x, end_y = event.x, event.y
        if abs(end_x - self.start_x) < 8 or abs(end_y - self.start_y) < 8:
            if self.rect:
                self.canvas.delete(self.rect)
            return

        x1, y1 = min(self.start_x, end_x), min(self.start_y, end_y)
        x2, y2 = max(self.start_x, end_x), max(self.start_y, end_y)

        ox  = x1 / self.scale
        oy  = y1 / self.scale
        ow  = (x2 - x1) / self.scale
        oh  = (y2 - y1) / self.scale

        if self.rect:
            self.canvas.delete(self.rect)

        # Hỏi text + class
        result = self._ask_box_info()
        if result:
            text, class_id = result
            self.draw_box([ox, oy, ow, oh], text, class_id)
            self.update_sidebar()

    def _ask_box_info(self):
        """Dialog nhập text và chọn class."""
        win = tk.Toplevel(self.master)
        win.title("Gán nhãn vùng mới")
        win.configure(bg="#1e293b")
        win.grab_set()

        tk.Label(
            win, text="Văn bản trong vùng (tiếng Trung, để trống nếu chưa biết):",
            fg="#94a3b8", bg="#1e293b", font=("Segoe UI", 10)
        ).pack(padx=16, pady=(16, 4))

        text_var = tk.StringVar()
        entry = tk.Entry(win, textvariable=text_var, font=("Consolas", 12),
                         bg="#0f172a", fg="#e2e8f0", insertbackground="white",
                         relief=tk.FLAT, bd=6)
        entry.pack(padx=16, fill=tk.X)
        entry.focus_set()

        tk.Label(
            win, text="Loại nhãn:",
            fg="#94a3b8", bg="#1e293b", font=("Segoe UI", 10)
        ).pack(padx=16, pady=(12, 4))

        class_var = tk.IntVar(value=self.active_class)
        for cls in CLASSES:
            tk.Radiobutton(
                win, text=cls["label"],
                variable=class_var, value=cls["id"],
                fg=cls["tk_color"], bg="#1e293b",
                selectcolor="#0f172a",
                font=("Segoe UI", 10, "bold"),
                activebackground="#1e293b"
            ).pack(anchor=tk.W, padx=24)

        result = [None]

        def confirm():
            result[0] = (text_var.get().strip(), class_var.get())
            win.destroy()

        def cancel():
            win.destroy()

        btn_frame = tk.Frame(win, bg="#1e293b")
        btn_frame.pack(pady=12, padx=16, fill=tk.X)
        tk.Button(
            btn_frame, text="Hủy", command=cancel,
            bg="#334155", fg="white", relief=tk.FLAT, padx=10
        ).pack(side=tk.RIGHT, padx=4)
        tk.Button(
            btn_frame, text="✔ Xác Nhận", command=confirm,
            bg="#22c55e", fg="white", relief=tk.FLAT, padx=10, font=("Segoe UI", 10, "bold")
        ).pack(side=tk.RIGHT)

        win.bind("<Return>", lambda e: confirm())
        win.bind("<Escape>", lambda e: cancel())
        win.wait_window()
        return result[0]

    def on_double_click(self, event):
        for i, b in enumerate(self.boxes):
            sx, sy = b['box'][0] * self.scale, b['box'][1] * self.scale
            sw, sh = b['box'][2] * self.scale, b['box'][3] * self.scale
            if sx <= event.x <= sx + sw and sy <= event.y <= sy + sh:
                self.on_double_click_box(i)
                break

    def on_double_click_box(self, idx):
        b = self.boxes[idx]
        cls = CLASSES[b['class_id']] if b['class_id'] < len(CLASSES) else CLASSES[0]

        action = messagebox.askyesnocancel(
            "Sửa / Xóa",
            f"Class: {cls['label']}\nChữ: {b['text']}\n\n"
            "Yes → Sửa  |  No → Xóa  |  Cancel → Thoát"
        )
        if action is True:
            result = self._ask_box_info()
            if result:
                new_text, new_class = result
                # Xóa canvas cũ và vẽ lại
                self.canvas.delete(b['id'])
                self.canvas.delete(b['text_id'])
                self.canvas.delete(b['cls_id_lbl'])
                self.boxes.pop(idx)
                self.draw_box(b['box'], new_text, new_class, b.get('polygon'))
                self.update_sidebar()
        elif action is False:
            self.canvas.delete(b['id'])
            self.canvas.delete(b['text_id'])
            self.canvas.delete(b['cls_id_lbl'])
            self.boxes.pop(idx)
            self.update_sidebar()

    # ------------------------------------------------------------------ #
    #  AI PSEUDO-LABEL                                                     #
    # ------------------------------------------------------------------ #
    def auto_predict(self):
        if not self.ocr:
            return
        path = self.image_paths[self.current_idx]
        print(f"[AI] Đang predict: {os.path.basename(path)}")
        result = self.ocr.ocr(self.original_img, cls=True)
        if result and result[0]:
            for line in result[0]:
                poly  = line[0]
                text  = line[1][0]
                xs    = [p[0] for p in poly]
                ys    = [p[1] for p in poly]
                x, y  = min(xs), min(ys)
                w, h  = max(xs) - x, max(ys) - y
                polygon = [[float(p[0]), float(p[1])] for p in poly]
                # Mặc định speech_bubble — user điều chỉnh sau
                self.draw_box([x, y, w, h], text, class_id=0, polygon=polygon)
        self.update_sidebar()

    # ------------------------------------------------------------------ #
    #  SAVE & NAVIGATE                                                     #
    # ------------------------------------------------------------------ #
    def save_and_next(self):
        path = self.image_paths[self.current_idx]
        self.all_labels[path] = [
            {
                "box":      b["box"],
                "text":     b["text"],
                "class_id": b["class_id"],
                "polygon":  b.get("polygon"),
            }
            for b in self.boxes
        ]
        self.save_labels()
        if self.current_idx < len(self.image_paths) - 1:
            self.current_idx += 1
            self.load_image()
        else:
            messagebox.showinfo("Hoàn thành", "Đã gán nhãn xong toàn bộ ảnh!")

    def prev_img(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self.load_image()

    # ------------------------------------------------------------------ #
    #  EXPORT YOLO DATASET                                                 #
    # ------------------------------------------------------------------ #
    def export_yolo(self):
        labels = self.all_labels
        if not labels:
            messagebox.showwarning("Export", "Chưa có nhãn nào!")
            return

        img_out = os.path.join(EXPORT_DIR, "images", "train")
        lbl_out = os.path.join(EXPORT_DIR, "labels", "train")
        os.makedirs(img_out, exist_ok=True)
        os.makedirs(lbl_out, exist_ok=True)

        exported = 0
        for img_path, boxes in labels.items():
            if not boxes or not os.path.exists(img_path):
                continue

            img_name = os.path.basename(img_path)
            shutil.copy2(img_path, os.path.join(img_out, img_name))

            img_cv = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img_cv is None:
                continue
            img_h, img_w = img_cv.shape[:2]

            stem     = Path(img_name).stem
            lbl_path = os.path.join(lbl_out, stem + ".txt")

            with open(lbl_path, 'w', encoding='utf-8') as lf:
                for box_data in boxes:
                    class_id = box_data.get("class_id", 0)
                    polygon  = box_data.get("polygon")
                    if polygon and len(polygon) >= 3:
                        pts = polygon
                    else:
                        bx, by, bw, bh = box_data["box"]
                        pts = [
                            [bx,      by],
                            [bx + bw, by],
                            [bx + bw, by + bh],
                            [bx,      by + bh],
                        ]
                    norm = []
                    for px, py in pts:
                        norm.extend([
                            f"{max(0.0, min(1.0, px/img_w)):.6f}",
                            f"{max(0.0, min(1.0, py/img_h)):.6f}"
                        ])
                    lf.write(f"{class_id} {' '.join(norm)}\n")

            exported += 1

        # data.yaml
        class_names = [c["name"] for c in CLASSES]
        yaml_content = (
            f"# YOLO v8 Segmentation Dataset\n"
            f"path: {EXPORT_DIR}\n"
            f"train: images/train\n"
            f"val:   images/train\n\n"
            f"nc: {len(CLASSES)}\n"
            f"names: {json.dumps(class_names, ensure_ascii=False)}\n"
        )
        with open(os.path.join(EXPORT_DIR, "data.yaml"), 'w') as yf:
            yf.write(yaml_content)

        messagebox.showinfo(
            "Export Thành Công",
            f"✅ Đã export {exported} ảnh!\n"
            f"📁 Thư mục: {EXPORT_DIR}\n"
            f"📄 Classes: {', '.join(class_names)}\n\n"
            "Bước tiếp theo:\n"
            "1. Upload yolo_export/ lên Google Drive\n"
            "2. Mở colab_training.ipynb trên Colab\n"
            "3. Chạy train!"
        )


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1400x900")
    root.configure(bg="#0e1117")
    app = ComicLabeler(root)
    root.mainloop()
