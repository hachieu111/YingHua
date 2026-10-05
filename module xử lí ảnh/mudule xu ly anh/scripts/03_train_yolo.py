"""
Script: 03_train_yolo.py
Mục tiêu: Fine-tune YOLOv8n để nhận diện bong bóng chat trong truyện tranh

Chiến lược Transfer Learning:
  - Dùng YOLOv8n.pt (pre-trained trên COCO)
  - Fine-tune trên dataset truyện tranh của bạn
  - Chỉ 1 class: speech_bubble
"""

import os
from pathlib import Path

# ==================== CẤU HÌNH ====================
DATASET_YAML = r"d:\PTUD\mudule xu ly anh\dataset\dataset.yaml"
OUTPUT_DIR   = r"d:\PTUD\mudule xu ly anh\runs\bubble_detector"
MODEL_OUTPUT = r"d:\PTUD\mudule xu ly anh\models\yolov8n_bubble.pt"

# Hyperparameters tối ưu cho dataset nhỏ (<200 ảnh)
EPOCHS    = 150
IMG_SIZE  = 1280   # Ảnh truyện tranh thường dài, cần imgsz cao
BATCH     = 4      # Giảm xuống 2 nếu hết RAM GPU/CPU
PATIENCE  = 30     # Early stopping sau 30 epoch không cải thiện


def train():
    try:
        from ultralytics import YOLO
    except ImportError:
        print("❌ Chưa cài ultralytics! Chạy: pip install ultralytics")
        return
    
    print("=" * 60)
    print("🚀 BƯỚC 3: Fine-tune YOLOv8n - Bubble Detector")
    print("=" * 60)
    print(f"\n  Dataset: {DATASET_YAML}")
    print(f"  Output:  {OUTPUT_DIR}")
    print(f"  Epochs:  {EPOCHS}")
    print(f"  ImgSize: {IMG_SIZE}")
    print(f"  Batch:   {BATCH}")
    
    # Kiểm tra dataset.yaml
    if not os.path.exists(DATASET_YAML):
        print(f"❌ Không tìm thấy dataset.yaml! Chạy script 01 trước.")
        return
    
    # Load model pretrained (tự download nếu chưa có)
    print("\n📥 Đang load YOLOv8n pretrained weights (COCO)...")
    model = YOLO("yolov8n.pt")
    
    print("\n🏋️  Bắt đầu training...")
    results = model.train(
        data=DATASET_YAML,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH,
        patience=PATIENCE,
        project=OUTPUT_DIR,
        name="exp1",
        
        # Augmentation của YOLO (bổ sung cho augmentation của bạn)
        # Tắt một số augment mạnh không phù hợp với truyện tranh
        flipud=0.0,       # KHÔNG flip dọc
        fliplr=0.5,       # Flip ngang (đã có trong script 02)
        degrees=5.0,      # Xoay ±5 độ
        translate=0.03,
        scale=0.2,
        shear=2.0,
        perspective=0.0,  # KHÔNG perspective (làm lệch bong bóng)
        hsv_h=0.015,      # Điều chỉnh màu sắc nhẹ
        hsv_s=0.4,
        hsv_v=0.3,
        mosaic=1.0,       # Mosaic augmentation (ghép 4 ảnh) - rất tốt
        mixup=0.0,        # MixUp không phù hợp
        
        # Optimizer settings phù hợp dataset nhỏ
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        warmup_epochs=5,
        
        # Saving
        save=True,
        save_period=20,   # Lưu checkpoint mỗi 20 epoch
        
        # Device: 'cpu' nếu không có GPU, '0' nếu có GPU
        device="cpu",     # Đổi thành '0' nếu có NVIDIA GPU
        
        verbose=True,
    )
    
    print("\n✅ Training hoàn tất!")
    print(f"   Best model tại: {OUTPUT_DIR}/exp1/weights/best.pt")
    
    # Validate model tốt nhất
    print("\n🔍 Đánh giá model tốt nhất trên tập val...")
    best_model = YOLO(f"{OUTPUT_DIR}/exp1/weights/best.pt")
    val_results = best_model.val(data=DATASET_YAML, imgsz=IMG_SIZE)
    
    print(f"\n📊 Kết quả Validation:")
    print(f"   mAP50:     {val_results.box.map50:.4f}")
    print(f"   mAP50-95:  {val_results.box.map:.4f}")
    print(f"   Precision: {val_results.box.mp:.4f}")
    print(f"   Recall:    {val_results.box.mr:.4f}")
    
    # Copy model tốt nhất về thư mục models/
    import shutil
    Path(MODEL_OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(f"{OUTPUT_DIR}/exp1/weights/best.pt", MODEL_OUTPUT)
    print(f"\n✅ Đã lưu model về: {MODEL_OUTPUT}")
    print(f"\nBước tiếp theo: Tích hợp model vào pipeline (src/pipeline.py)")


def test_single_image(img_path: str):
    """Kiểm tra nhanh model với 1 ảnh"""
    from ultralytics import YOLO
    import cv2
    
    if not os.path.exists(MODEL_OUTPUT):
        print(f"❌ Chưa có model! Train trước.")
        return
    
    model = YOLO(MODEL_OUTPUT)
    results = model.predict(img_path, imgsz=IMG_SIZE, conf=0.3)
    
    # Hiển thị kết quả
    for r in results:
        print(f"Phát hiện {len(r.boxes)} bong bóng chat:")
        for box in r.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = box.conf[0].item()
            print(f"  Bubble tại ({x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}) - confidence: {conf:.2f}")
        
        # Lưu ảnh kết quả
        output_img = r.plot()
        output_path = "test_detection_result.jpg"
        cv2.imencode('.jpg', output_img)[1].tofile(output_path)
        print(f"\nKết quả đã lưu tại: {output_path}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Chạy: python 03_train_yolo.py test <đường_dẫn_ảnh>
        img = sys.argv[2] if len(sys.argv) > 2 else None
        if img:
            test_single_image(img)
        else:
            print("Usage: python 03_train_yolo.py test <image_path>")
    else:
        train()
