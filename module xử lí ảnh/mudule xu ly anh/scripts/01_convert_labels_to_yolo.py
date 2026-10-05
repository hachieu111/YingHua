"""
Script: 01_convert_labels_to_yolo.py
Mục tiêu: Chuyển đổi labels.txt sang format YOLO để train YOLOv8

Logic:
  - Mỗi ảnh có nhiều text-lines, mỗi text-line có bbox [x, y, w, h]
  - Tự động gom các text-lines gần nhau thành BUBBLE BBOX
    bằng cách dùng convex hull + padding
  - Output: file .txt chuẩn YOLO cho mỗi ảnh, chia train/val
"""

import json
import os
import shutil
import random
import cv2
import numpy as np
from pathlib import Path

# ==================== CẤU HÌNH ====================
LABEL_FILE = r"d:\PTUD\mudule xu ly anh\labels.txt"
OUTPUT_DIR = r"d:\PTUD\mudule xu ly anh\dataset"
TRAIN_RATIO = 0.80   # 80% train, 20% val
RANDOM_SEED = 42
BUBBLE_PADDING = 15  # Pixel padding thêm quanh bubble bbox
# Khoảng cách tối đa (px) để gom 2 text-lines vào 1 bubble
MERGE_THRESHOLD = 120

# Class IDs cho YOLO
CLASS_BUBBLE = 0  # speech_bubble (bubble chứa đoạn thoại)


def load_labels(label_file: str) -> dict:
    """Load labels.txt → {image_path: [{box, text}]}"""
    labels = {}
    with open(label_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) == 2:
                img_path = parts[0]
                boxes = json.loads(parts[1])
                labels[img_path] = boxes
    return labels


def get_image_size(img_path: str):
    """Lấy kích thước ảnh (width, height)"""
    img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Không tìm thấy ảnh: {img_path}")
    return img.shape[1], img.shape[0]  # width, height


def boxes_overlap_or_near(box1, box2, threshold=MERGE_THRESHOLD):
    """
    Kiểm tra 2 bounding box có gần nhau không.
    box format: [x, y, w, h]
    """
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    
    # Mở rộng mỗi box bằng threshold để kiểm tra lân cận
    r1 = (x1 - threshold, y1 - threshold, x1 + w1 + threshold, y1 + h1 + threshold)
    r2 = (x2, y2, x2 + w2, y2 + h2)
    
    # Kiểm tra giao nhau
    overlap_x = r1[0] < r2[2] and r1[2] > r2[0]
    overlap_y = r1[1] < r2[3] and r1[3] > r2[1]
    return overlap_x and overlap_y


def merge_boxes_into_bubbles(text_boxes, merge_threshold=MERGE_THRESHOLD):
    """
    Gom các text_boxes gần nhau thành 1 bubble.
    Dùng thuật toán Union-Find để gom nhóm.
    
    Returns: List[tuple(x, y, w, h)] - danh sách bubble bbox
    """
    n = len(text_boxes)
    if n == 0:
        return []
    
    # Union-Find
    parent = list(range(n))
    
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    # Gom các box gần nhau
    for i in range(n):
        for j in range(i + 1, n):
            if boxes_overlap_or_near(text_boxes[i]['box'], text_boxes[j]['box'], merge_threshold):
                union(i, j)
    
    # Nhóm các boxes theo cluster
    clusters = {}
    for i in range(n):
        root = find(i)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(text_boxes[i]['box'])
    
    # Tính bounding box bao quanh mỗi cluster (= 1 bubble)
    bubbles = []
    for cluster_boxes in clusters.values():
        all_x1 = [b[0] for b in cluster_boxes]
        all_y1 = [b[1] for b in cluster_boxes]
        all_x2 = [b[0] + b[2] for b in cluster_boxes]
        all_y2 = [b[1] + b[3] for b in cluster_boxes]
        
        bx = max(0, min(all_x1) - BUBBLE_PADDING)
        by = max(0, min(all_y1) - BUBBLE_PADDING)
        bw = max(all_x2) - min(all_x1) + 2 * BUBBLE_PADDING
        bh = max(all_y2) - min(all_y1) + 2 * BUBBLE_PADDING
        bubbles.append((bx, by, bw, bh))
    
    return bubbles


def convert_to_yolo_format(x, y, w, h, img_width, img_height):
    """
    Convert [x, y, w, h] (absolute pixel) → YOLO format (normalized center)
    YOLO: x_center, y_center, width, height (tất cả 0..1)
    """
    x_center = (x + w / 2) / img_width
    y_center = (y + h / 2) / img_height
    width_norm = w / img_width
    height_norm = h / img_height
    
    # Clamp về [0, 1]
    x_center = max(0.0, min(1.0, x_center))
    y_center = max(0.0, min(1.0, y_center))
    width_norm = max(0.001, min(1.0, width_norm))
    height_norm = max(0.001, min(1.0, height_norm))
    
    return x_center, y_center, width_norm, height_norm


def create_output_structure(output_dir: str):
    """Tạo cấu trúc thư mục dataset chuẩn YOLO"""
    for split in ['train', 'val']:
        for folder in ['images', 'labels']:
            Path(os.path.join(output_dir, folder, split)).mkdir(parents=True, exist_ok=True)
    print(f"✅ Đã tạo cấu trúc thư mục tại: {output_dir}")


def write_yaml(output_dir: str):
    """Tạo file dataset.yaml cho YOLOv8"""
    yaml_content = f"""# YOLOv8 Dataset Config - Comic Speech Bubble Detector
path: {output_dir}
train: images/train
val: images/val

# Classes
nc: 1
names: ['speech_bubble']

# Ghi chú:
# speech_bubble = bong bóng chat chứa đoạn thoại trong truyện tranh
"""
    yaml_path = os.path.join(output_dir, 'dataset.yaml')
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)
    print(f"✅ Đã tạo: {yaml_path}")


def main():
    print("=" * 60)
    print("🚀 BƯỚC 1: Chuyển đổi Dataset sang Format YOLO")
    print("=" * 60)
    
    # Load labels
    print(f"\n📂 Đang load: {LABEL_FILE}")
    labels = load_labels(LABEL_FILE)
    valid_entries = {k: v for k, v in labels.items() if v and os.path.exists(k)}
    
    print(f"   Tổng entries: {len(labels)}")
    print(f"   Entries hợp lệ (ảnh tồn tại): {len(valid_entries)}")
    
    if len(valid_entries) == 0:
        print("❌ Không tìm thấy ảnh nào! Kiểm tra đường dẫn.")
        return
    
    # Tạo thư mục
    create_output_structure(OUTPUT_DIR)
    
    # Shuffle và split
    all_paths = list(valid_entries.keys())
    random.seed(RANDOM_SEED)
    random.shuffle(all_paths)
    
    split_idx = int(len(all_paths) * TRAIN_RATIO)
    train_paths = all_paths[:split_idx]
    val_paths = all_paths[split_idx:]
    
    print(f"\n📊 Phân chia dataset:")
    print(f"   Train: {len(train_paths)} ảnh")
    print(f"   Val:   {len(val_paths)} ảnh")
    
    stats = {"train": {"images": 0, "bubbles": 0}, "val": {"images": 0, "bubbles": 0}}
    
    # Xử lý từng ảnh
    for split, paths in [("train", train_paths), ("val", val_paths)]:
        print(f"\n🔄 Đang xử lý tập {split.upper()}...")
        
        for img_path in paths:
            try:
                # Lấy kích thước ảnh
                img_w, img_h = get_image_size(img_path)
                
                # Lấy text boxes của ảnh này
                text_boxes = valid_entries[img_path]
                
                # Gom text boxes thành bubble bbox
                bubbles = merge_boxes_into_bubbles(text_boxes)
                
                if not bubbles:
                    print(f"  ⚠️  Bỏ qua (không có bubble): {os.path.basename(img_path)}")
                    continue
                
                # Tên file base (không có extension)
                basename = Path(img_path).stem
                ext = Path(img_path).suffix
                
                # Copy ảnh vào thư mục dataset
                dst_img = os.path.join(OUTPUT_DIR, "images", split, basename + ext)
                shutil.copy2(img_path, dst_img)
                
                # Tạo file label YOLO
                dst_label = os.path.join(OUTPUT_DIR, "labels", split, basename + ".txt")
                with open(dst_label, 'w') as f:
                    for (bx, by, bw, bh) in bubbles:
                        # Đảm bảo bbox không vượt quá ảnh
                        bw = min(bw, img_w - bx)
                        bh = min(bh, img_h - by)
                        
                        xc, yc, wn, hn = convert_to_yolo_format(bx, by, bw, bh, img_w, img_h)
                        f.write(f"{CLASS_BUBBLE} {xc:.6f} {yc:.6f} {wn:.6f} {hn:.6f}\n")
                
                stats[split]["images"] += 1
                stats[split]["bubbles"] += len(bubbles)
                print(f"  ✓ {os.path.basename(img_path):30s} → {len(bubbles)} bubbles")
                
            except FileNotFoundError as e:
                print(f"  ❌ Lỗi: {e}")
            except Exception as e:
                print(f"  ❌ Lỗi xử lý {img_path}: {e}")
    
    # Tạo dataset.yaml
    write_yaml(OUTPUT_DIR)
    
    # In tổng kết
    print("\n" + "=" * 60)
    print("✅ HOÀN TẤT!")
    print("=" * 60)
    print(f"Train: {stats['train']['images']} ảnh, {stats['train']['bubbles']} bubbles")
    print(f"Val:   {stats['val']['images']} ảnh, {stats['val']['bubbles']} bubbles")
    print(f"\nDataset đã sẵn sàng tại: {OUTPUT_DIR}")
    print(f"Bước tiếp theo: Chạy script 02_augment_dataset.py")


if __name__ == "__main__":
    main()
