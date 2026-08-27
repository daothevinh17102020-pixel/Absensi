# config.example.py — TEMPLATE KONFIGURASI
# =====================================================
# CARA PAKAI:
# 1. Salin file ini, rename menjadi config.py
# 2. Isi semua nilai yang bertanda  <-- GANTI INI
# 3. Jangan pernah upload config.py ke GitHub!
# =====================================================

# === KONFIGURASI DATABASE ===
DB_CONFIG = {
    'host'    : 'localhost',
    'port'    : 3306,
    'user'    : 'root',
    'password': 'GANTI_PASSWORD_MYSQL_ANDA',   # <-- GANTI INI
    'database': 'absensi_db'
}

# Untuk database cloud, isi path CA yang benar untuk sistem operasi Anda.
# DB_CONFIG['ssl_ca'] = r'C:\\path\\to\\ca.pem'
# DB_CONFIG['ssl_verify_cert'] = True

# === KONFIGURASI SISTEM ===
DATASET_PATH         = 'dataset'
# Engine scan realtime: YOLOv8n-Face 5 landmarks -> ArcFace embedding.
# Hai ONNX model phai do operator da co quyen su dung dat vao may; khong commit
# weight atau gallery sinh trac hoc vao Git.
MODEL_PATH           = 'models/trainer.yml'
FACE_DETECTOR_MODEL_PATH = 'models/yolo/yolov8n-face-5kps.onnx'
FACE_RECOGNITION_MODEL_PATH = 'models/arcface/w600k_r50.onnx'
FACE_MODEL_ROOT      = 'models/insightface'
FACE_GALLERY_PATH    = 'models/face_gallery.npz'
FACE_GALLERY_META_PATH = 'models/face_gallery.json'
FACE_MODEL_PACK      = 'buffalo_l'
FACE_DET_SIZE        = 640
FACE_DETECTOR_CONFIDENCE = 0.45
FACE_DETECTOR_NMS_IOU = 0.45
FACE_MAX_DETECTIONS = 10
FACE_EMBEDDING_REFRESH_SECONDS = 2.0
FACE_COMPLETED_TRACK_TTL_SECONDS = 8.0
FACE_GALLERY_STAT_INTERVAL_SECONDS = 1.0
FACE_TRACK_TTL_SECONDS = 2.0
FACE_TRACK_IOU_THRESHOLD = 0.25
FACE_MIN_SIZE = 64
FACE_MIN_BRIGHTNESS = 45
FACE_MAX_BRIGHTNESS = 220
FACE_MIN_BLUR_VARIANCE = 40
FACE_ORT_THREADS = 4
# De trong cho den khi da hieu chuan bang test camera. Vi du sau hieu chuan:
# FACE_MATCH_THRESHOLD = 0.50
FACE_MATCH_THRESHOLD = None
CONFIDENCE_THRESHOLD = 45
# 24 accepted images: 6 centre, 5 left, 5 right, 4 near, 4 far.
FOTO_PER_USER        = 24
ENROLLMENT_MIN_SIZE = 110
ENROLLMENT_MIN_BRIGHTNESS = 60
ENROLLMENT_MAX_BRIGHTNESS = 200
ENROLLMENT_MIN_BLUR_VARIANCE = 75
ENROLLMENT_POSE_YAW_RATIO = 0.18
ENROLLMENT_FACE_MIN_RATIO = 0.035
ENROLLMENT_FACE_MAX_RATIO = 0.42
ENROLLMENT_NEAR_MIN_RATIO = 0.15
ENROLLMENT_FAR_MIN_RATIO = 0.035
ENROLLMENT_FAR_MAX_RATIO = 0.09
ENROLLMENT_STABLE_FRAMES = 3
ENROLLMENT_STATE_TTL_SECONDS = 300
FACE_GALLERY_MAX_TEMPLATES_PER_USER = 12
# Do not lower the recognition threshold; this margin rejects ambiguous matches.
FACE_MATCH_MIN_MARGIN = 0.03
CAMERA_INDEX         = 0    # 0 = webcam bawaan, 1 = webcam eksternal
SNAPSHOT_PATH        = 'snapshots'
TOLERANSI_MENIT      = 15
ABSENSI_GRACE_MINUTES = 30  # Waktu tambahan setelah kelas berakhir
RECOGNITION_REQUIRED_FRAMES = 3
APP_TIMEZONE         = 'Asia/Jakarta'

# === KONFIGURASI ANTI-SPOOFING ===
ANTI_SPOOFING_ENABLED   = False
ANTI_SPOOFING_THRESHOLD = 0.5

# === KONFIGURASI FLASK ===
FLASK_HOST  = '0.0.0.0'
FLASK_PORT  = 5000
FLASK_DEBUG = True
FLASK_SECRET_KEY = 'GANTI_DENGAN_RANDOM_SECRET_KEY'

# === KONFIGURASI ESP32 ===
ESP32_ENABLED = False          # Ganti True jika ESP32 sudah tersedia
ESP32_IP      = '192.168.X.X' # <-- GANTI dengan IP ESP32 Anda
ESP32_PORT    = 80
ESP32_TIMEOUT = 3
