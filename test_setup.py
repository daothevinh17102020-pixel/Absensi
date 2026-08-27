# test_setup.py

from importlib.metadata import version


print("=== TES PERSIAPAN SISTEM ABSENSI ===\n")

# Tes 1: NumPy
try:
    import numpy as np
    print(f"[OK] NumPy {np.__version__}")
except: print("[GAGAL] NumPy")

# Tes 2: OpenCV
try:
    import cv2
    print(f"[OK] OpenCV {cv2.__version__}")
except: print("[GAGAL] OpenCV")

# Tes 3: InsightFace ArcFace + model asset lokal
try:
    from face.recognition import ensure_model_ready
    model_info = ensure_model_ready()
    print("[OK] YOLOv8-Face + ArcFace ONNX siap")
except Exception as e: print(f"[GAGAL] Model ONNX/Runtime - {e}")

# Tes 4: Webcam
try:
    cam = cv2.VideoCapture(0)
    if cam.isOpened():
        print("[OK] Webcam terdeteksi")
        cam.release()
    else:
        print("[PERINGATAN] Webcam tidak terdeteksi")
except: print("[GAGAL] Webcam")

# Tes 5: Flask
try:
    import flask
    print(f"[OK] Flask {version('Flask')}")
except: print("[GAGAL] Flask")

# Tes 6: MySQL
try:
    import mysql.connector
    from config import DB_CONFIG
    conn = mysql.connector.connect(**DB_CONFIG)
    if conn.is_connected():
        print("[OK] Koneksi MySQL berhasil")
        conn.close()
except Exception as e:
    print(f"[GAGAL] MySQL — {e}")

# Tes 7: Pillow
try:
    from PIL import Image
    print("[OK] Pillow tersedia")
except: print("[GAGAL] Pillow")

# Tes 8: requests
try:
    import requests
    print(f"[OK] Requests {requests.__version__}")
except: print("[GAGAL] requests")

print("\n=== TES SELESAI ===")
