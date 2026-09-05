# test_setup.py — Kiểm tra môi trường hệ thống điểm danh

import sys
from importlib.metadata import version

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


print("=== KIỂM TRA MÔI TRƯỜNG HỆ THỐNG ĐIỂM DANH ===\n")

# Kiểm tra 1: NumPy
try:
    import numpy as np
    print(f"[OK] NumPy {np.__version__}")
except: print("[THẤT BẠI] NumPy")

# Kiểm tra 2: OpenCV
try:
    import cv2
    print(f"[OK] OpenCV {cv2.__version__}")
except: print("[THẤT BẠI] OpenCV")

# Kiểm tra 3: InsightFace ArcFace + model asset nội bộ
try:
    from face.recognition import ensure_model_ready
    model_info = ensure_model_ready()
    print("[OK] YOLOv8-Face + ArcFace ONNX sẵn sàng")
except Exception as e: print(f"[THẤT BẠI] Model ONNX/Runtime - {e}")

# Kiểm tra 4: Webcam
try:
    cam = cv2.VideoCapture(0)
    if cam.isOpened():
        print("[OK] Camera hoạt động bình thường")
        cam.release()
    else:
        print("[CẢNH BÁO] Không tìm thấy camera khả dụng")
except: print("[THẤT BẠI] Camera")

# Kiểm tra 5: Flask
try:
    import flask
    print(f"[OK] Flask {version('Flask')}")
except: print("[THẤT BẠI] Flask")

# Kiểm tra 6: MySQL
try:
    import mysql.connector
    from config import DB_CONFIG
    conn = mysql.connector.connect(**DB_CONFIG)
    if conn.is_connected():
        print("[OK] Kết nối MySQL thành công")
        conn.close()
except Exception as e:
    print(f"[THẤT BẠI] MySQL — {e}")

# Kiểm tra 7: Pillow
try:
    from PIL import Image
    print("[OK] Pillow hoạt động")
except: print("[THẤT BẠI] Pillow")

# Kiểm tra 8: requests
try:
    import requests
    print(f"[OK] Requests {requests.__version__}")
except: print("[THẤT BẠI] requests")

print("\n=== HOÀN TẤT KIỂM TRA ===")
