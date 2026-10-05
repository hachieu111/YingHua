"""
Script: 02_augment_dataset.py
Mục tiêu: Tăng cường dữ liệu (Data Augmentation) cho dataset truyện tranh

Từ 26 ảnh → ~130+ ảnh hiệu quả
Dùng thư viện Albumentations (tối ưu cho Computer Vision)
"""

import os
import cv2
import numpy as np
from pathlib import Path
import albumentations as A
import random

# ==================== CẤU HÌNH ====================
DATASET_DIR = r"d:\PTUD\mudule xu ly anh\dataset"
# Số lượng bản augmented tạo ra cho mỗi ảnh train
AUG_PER_IMAGE = 4
RANDOM_SEED = 42


def load_yolo_labels(label_path: str):
    """Load YOLO label file → list of [class_id, xc, yc, w, h]"""
    boxes = []
    if not os.path.exists(label_path):
        return boxes
    with open(label_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 5:
                class_id = int(parts[0])
                xc, yc, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                boxes.append([class_id, xc, yc, w, h])
    return boxes


def save_yolo_labels(boxes, label_path: str, img_h: int, img_w: int):
    """Lưu boxes (từ albumentations output) về file YOLO format"""
    with open(label_path, 'w') as f:
        for box in boxes:
            # albumentations trả về [x_min, y_min, x_max, y_max] (0..1)
            x_min, y_min, x_max, y_max = box[:4]
            class_id = int(box[4])
            
            xc = (x_min + x_max) / 2
            yc = (y_min + y_max) / 2
            w = x_max - x_min
            h = y_max - y_min
            
            # Clamp
            xc = max(0.001, min(0.999, xc))
            yc = max(0.001, min(0.999, yc))
            w = max(0.001, min(0.999, w))
            h = max(0.001, min(0.999, h))
            
            f.write(f"{class_id} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n")


def yolo_to_albumentations(boxes):
    """
    YOLO [class_id, xc, yc, w, h] → Albumentations [x_min, y_min, x_max, y_max, class_id]
    Albumentations dùng format pascal_voc normalized
    """
    result = []
    for box in boxes:
        class_id, xc, yc, w, h = box
        x_min = max(0.0, xc - w / 2)
        y_min = max(0.0, yc - h / 2)
        x_max = min(1.0, xc + w / 2)
        y_max = min(1.0, yc + h / 2)
        result.append([x_min, y_min, x_max, y_max, class_id])
    return result


def build_augmentation_pipeline():
    """
    Tạo Augmentation Pipeline phù hợp với truyện tranh.
    
    KHÔNG dùng:
    - Vertical flip (chữ Trung sẽ ngược)
    - Perspective mạnh (làm lệch bong bóng quá nhiều)
    - Hue/Saturation (nhiều trang là ảnh trắng đen)
    """
    return A.Compose([
        # === Geometric transforms (nhẹ, an toàn) ===
        A.HorizontalFlip(p=0.5),
        A.Rotate(
            limit=5,           # Xoay tối đa ±5 độ
            border_mode=cv2.BORDER_CONSTANT,
            value=255,         # Nền trắng khi xoay
            p=0.4
        ),
        A.ShiftScaleRotate(
            shift_limit=0.03,  # Dịch chuyển nhẹ
            scale_limit=0.1,   # Scale ±10%
            rotate_limit=3,
            border_mode=cv2.BORDER_CONSTANT,
            value=255,
            p=0.3
        ),
        
        # === Brightness / Contrast (giả lập chất lượng scan khác nhau) ===
        A.OneOf([
            A.RandomBrightnessContrast(
                brightness_limit=0.2,
                contrast_limit=0.2,
                p=1.0
            ),
            A.CLAHE(clip_limit=2.0, p=1.0),  # Tăng độ tương phản cục bộ
        ], p=0.5),
        
        # === Noise / Blur (giả lập ảnh scan cũ, kém chất lượng) ===
        A.OneOf([
            A.GaussNoise(var_limit=(5.0, 20.0), p=1.0),
            A.ISONoise(color_shift=(0.01, 0.05), p=1.0),
            A.GaussianBlur(blur_limit=(1, 3), p=1.0),
        ], p=0.3),
        
        # === Compression artifacts (giả lập JPEG compressed) ===
        A.ImageCompression(
            quality_lower=70,
            quality_upper=100,
            p=0.2
        ),
        
        # === Phân tích màu sắc (một số trang có màu, một số không) ===
        A.ToGray(p=0.1),  # Thi thoảng convert sang grayscale

    ], bbox_params=A.BboxParams(
        format='albumentations',  # [x_min, y_min, x_max, y_max] normalized
        label_fields=['class_labels'],
        min_visibility=0.5  # Bỏ box nếu <50% bị crop mất
    ))


def augment_dataset():
    """Chạy augmentation cho tất cả ảnh trong tập train"""
    print("=" * 60)
    print("🚀 BƯỚC 2: Data Augmentation")
    print("=" * 60)
    
    train_img_dir = os.path.join(DATASET_DIR, "images", "train")
    train_lbl_dir = os.path.join(DATASET_DIR, "labels", "train")
    
    # Lấy danh sách ảnh train
    img_files = [f for f in os.listdir(train_img_dir) 
                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    print(f"\n📁 Tìm thấy {len(img_files)} ảnh train gốc")
    print(f"📈 Sẽ tạo thêm {AUG_PER_IMAGE} bản augmented/ảnh")
    print(f"📊 Tổng ảnh sau augmentation: ~{len(img_files) * (1 + AUG_PER_IMAGE)}")
    
    transform = build_augmentation_pipeline()
    random.seed(RANDOM_SEED)
    
    total_created = 0
    for img_file in img_files:
        img_path = os.path.join(train_img_dir, img_file)
        stem = Path(img_file).stem
        ext = Path(img_file).suffix
        lbl_path = os.path.join(train_lbl_dir, stem + ".txt")
        
        # Load ảnh
        img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print(f"  ❌ Không đọc được: {img_file}")
            continue
        
        img_h, img_w = img.shape[:2]
        
        # Load nhãn YOLO
        boxes_yolo = load_yolo_labels(lbl_path)
        if not boxes_yolo:
            print(f"  ⚠️  Không có nhãn: {img_file}")
            continue
        
        # Chuyển sang format albumentations
        boxes_albu = yolo_to_albumentations(boxes_yolo)
        bboxes = [[b[0], b[1], b[2], b[3]] for b in boxes_albu]
        class_labels = [int(b[4]) for b in boxes_albu]
        
        # Tạo AUG_PER_IMAGE bản augmented
        for aug_idx in range(AUG_PER_IMAGE):
            try:
                augmented = transform(
                    image=img,
                    bboxes=bboxes,
                    class_labels=class_labels
                )
                
                aug_img = augmented['image']
                aug_bboxes = augmented['bboxes']
                aug_class_labels = augmented['class_labels']
                
                if not aug_bboxes:
                    continue  # Skip nếu tất cả box bị crop mất
                
                # Tên file augmented
                aug_name = f"{stem}_aug{aug_idx:02d}"
                
                # Lưu ảnh
                dst_img = os.path.join(train_img_dir, aug_name + ext)
                cv2.imencode(ext, aug_img)[1].tofile(dst_img)
                
                # Lưu nhãn
                dst_lbl = os.path.join(train_lbl_dir, aug_name + ".txt")
                boxes_to_save = [[*b, c] for b, c in zip(aug_bboxes, aug_class_labels)]
                save_yolo_labels(boxes_to_save, dst_lbl, img_h, img_w)
                
                total_created += 1
                
            except Exception as e:
                print(f"  ⚠️  Augmentation thất bại ({img_file}, aug {aug_idx}): {e}")
        
        print(f"  ✓ {img_file:35s} → +{AUG_PER_IMAGE} augmented")
    
    print(f"\n✅ HOÀN TẤT! Đã tạo {total_created} ảnh augmented")
    print(f"   Thư mục train bây giờ có ~{len(img_files) + total_created} ảnh")


if __name__ == "__main__":
    augment_dataset()
