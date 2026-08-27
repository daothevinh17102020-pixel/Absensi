# config.py — Konfigurasi aplikasi dari Environment Variables
# File ini aman untuk di-commit ke GitHub karena tidak berisi password
# Semua nilai sensitif diambil dari Environment Variables

import os
import secrets
import json

# === KONFIGURASI DATABASE ===
# Nilai diambil dari Environment Variables Railway/Vercel
DB_CONFIG = {
    'host'    : os.environ.get('DB_HOST', 'localhost'),
    'port'    : int(os.environ.get('DB_PORT', 3306)),
    'user'    : os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'absensi_db'),
}

# Tambahkan SSL jika diperlukan (Aiven membutuhkan SSL)
if os.environ.get('DB_SSL_MODE') == 'REQUIRED':
    ssl_ca = os.environ.get('DB_SSL_CA')
    if ssl_ca:
        DB_CONFIG['ssl_ca'] = ssl_ca
    DB_CONFIG['ssl_verify_cert'] = True

# === KONFIGURASI SISTEM ===
DATASET_PATH         = os.environ.get('DATASET_PATH', 'dataset')
# MODEL_PATH dipertahankan untuk kompatibilitas file legacy; engine aktif tidak
# memakai LBPH/trainer.yml lagi.
MODEL_PATH           = os.environ.get('MODEL_PATH', 'models/trainer.yml')
# Model assets are installed by the operator (and must not be committed).
# Detector contract: decoded YOLOv8-Face ONNX output with xywh, score and five
# landmarks. Recognition contract: ArcFace-compatible ONNX embedding model.
FACE_DETECTOR_MODEL_PATH = os.environ.get(
    'FACE_DETECTOR_MODEL_PATH', 'models/yolo/yolov8n-face-5kps.onnx'
)
FACE_RECOGNITION_MODEL_PATH = os.environ.get(
    'FACE_RECOGNITION_MODEL_PATH',
    'models/insightface/models/buffalo_l/w600k_r50.onnx',
)
FACE_MODEL_ROOT      = os.environ.get('FACE_MODEL_ROOT', 'models/insightface')
FACE_GALLERY_PATH    = os.environ.get('FACE_GALLERY_PATH', 'models/face_gallery.npz')
FACE_GALLERY_META_PATH = os.environ.get('FACE_GALLERY_META_PATH', 'models/face_gallery.json')
FACE_MODEL_PACK      = os.environ.get('FACE_MODEL_PACK', 'buffalo_l')  # legacy
FACE_DET_SIZE        = int(os.environ.get('FACE_DET_SIZE', 640))
FACE_DETECTOR_CONFIDENCE = float(os.environ.get('FACE_DETECTOR_CONFIDENCE', 0.45))
FACE_DETECTOR_NMS_IOU = float(os.environ.get('FACE_DETECTOR_NMS_IOU', 0.45))
FACE_MAX_DETECTIONS = max(1, int(os.environ.get('FACE_MAX_DETECTIONS', 10)))
FACE_EMBEDDING_REFRESH_SECONDS = max(
    0.1, float(os.environ.get('FACE_EMBEDDING_REFRESH_SECONDS', 2.0))
)
FACE_COMPLETED_TRACK_TTL_SECONDS = max(
    1.0, float(os.environ.get('FACE_COMPLETED_TRACK_TTL_SECONDS', 8.0))
)
FACE_GALLERY_STAT_INTERVAL_SECONDS = max(
    0.1, float(os.environ.get('FACE_GALLERY_STAT_INTERVAL_SECONDS', 1.0))
)
FACE_TRACK_TTL_SECONDS = max(0.5, float(os.environ.get('FACE_TRACK_TTL_SECONDS', 2.0)))
FACE_TRACK_IOU_THRESHOLD = min(
    0.95, max(0.05, float(os.environ.get('FACE_TRACK_IOU_THRESHOLD', 0.25)))
)
FACE_MIN_SIZE = max(32, int(os.environ.get('FACE_MIN_SIZE', 64)))
FACE_MIN_BRIGHTNESS = float(os.environ.get('FACE_MIN_BRIGHTNESS', 45))
FACE_MAX_BRIGHTNESS = float(os.environ.get('FACE_MAX_BRIGHTNESS', 220))
FACE_MIN_BLUR_VARIANCE = float(os.environ.get('FACE_MIN_BLUR_VARIANCE', 40))
FACE_ORT_THREADS = max(1, int(os.environ.get('FACE_ORT_THREADS', 4)))
_face_match_threshold_raw = os.environ.get('FACE_MATCH_THRESHOLD', '').strip()
if _face_match_threshold_raw:
    FACE_MATCH_THRESHOLD = float(_face_match_threshold_raw)
else:
    # Local calibration is deliberately ignored by Git because it belongs to
    # the exact gallery/model pair on this machine. Environment still wins for
    # deployment and can explicitly keep the threshold unset.
    _calibration_path = os.environ.get(
        'FACE_CALIBRATION_PATH', 'models/face_calibration.local.json'
    )
    try:
        with open(_calibration_path, 'r', encoding='utf-8') as _calibration_file:
            _calibration = json.load(_calibration_file)
        FACE_MATCH_THRESHOLD = float(_calibration['configured_local_threshold'])
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        FACE_MATCH_THRESHOLD = None
# Bien legacy hien thi tren dashboard/source cu; khong dung de ra quyet dinh.
CONFIDENCE_THRESHOLD = int(os.environ.get('CONFIDENCE_THRESHOLD', 45))
# Enrollment keeps fewer, validated samples rather than 50 near-duplicates.
FOTO_PER_USER        = int(os.environ.get('FOTO_PER_USER', 24))
ENROLLMENT_MIN_SIZE = max(64, int(os.environ.get('ENROLLMENT_MIN_SIZE', 110)))
ENROLLMENT_MIN_BRIGHTNESS = float(os.environ.get('ENROLLMENT_MIN_BRIGHTNESS', 60))
ENROLLMENT_MAX_BRIGHTNESS = float(os.environ.get('ENROLLMENT_MAX_BRIGHTNESS', 200))
ENROLLMENT_MIN_BLUR_VARIANCE = float(os.environ.get('ENROLLMENT_MIN_BLUR_VARIANCE', 75))
ENROLLMENT_POSE_YAW_RATIO = min(0.45, max(0.05, float(os.environ.get('ENROLLMENT_POSE_YAW_RATIO', 0.18))))
ENROLLMENT_FACE_MIN_RATIO = min(0.50, max(0.01, float(os.environ.get('ENROLLMENT_FACE_MIN_RATIO', 0.035))))
ENROLLMENT_FACE_MAX_RATIO = min(0.90, max(ENROLLMENT_FACE_MIN_RATIO, float(os.environ.get('ENROLLMENT_FACE_MAX_RATIO', 0.42))))
ENROLLMENT_NEAR_MIN_RATIO = min(ENROLLMENT_FACE_MAX_RATIO, max(ENROLLMENT_FACE_MIN_RATIO, float(os.environ.get('ENROLLMENT_NEAR_MIN_RATIO', 0.15))))
ENROLLMENT_FAR_MIN_RATIO = min(ENROLLMENT_FACE_MAX_RATIO, max(ENROLLMENT_FACE_MIN_RATIO, float(os.environ.get('ENROLLMENT_FAR_MIN_RATIO', 0.035))))
ENROLLMENT_FAR_MAX_RATIO = min(ENROLLMENT_FACE_MAX_RATIO, max(ENROLLMENT_FAR_MIN_RATIO, float(os.environ.get('ENROLLMENT_FAR_MAX_RATIO', 0.09))))
ENROLLMENT_STABLE_FRAMES = max(1, int(os.environ.get('ENROLLMENT_STABLE_FRAMES', 3)))
ENROLLMENT_STATE_TTL_SECONDS = max(30.0, float(os.environ.get('ENROLLMENT_STATE_TTL_SECONDS', 300)))
FACE_GALLERY_MAX_TEMPLATES_PER_USER = max(1, int(os.environ.get('FACE_GALLERY_MAX_TEMPLATES_PER_USER', 12)))
FACE_MATCH_MIN_MARGIN = max(0.0, float(os.environ.get('FACE_MATCH_MIN_MARGIN', 0.03)))
CAMERA_INDEX         = int(os.environ.get('CAMERA_INDEX', 0))
SNAPSHOT_PATH        = os.environ.get('SNAPSHOT_PATH', 'snapshots')
TOLERANSI_MENIT      = int(os.environ.get('TOLERANSI_MENIT', 15))
ABSENSI_GRACE_MINUTES = max(0, int(os.environ.get('ABSENSI_GRACE_MINUTES', 30)))
RECOGNITION_REQUIRED_FRAMES = max(
    1, int(os.environ.get('RECOGNITION_REQUIRED_FRAMES', 3))
)
APP_TIMEZONE         = os.environ.get('APP_TIMEZONE', 'Asia/Jakarta')

# === KONFIGURASI ANTI-SPOOFING ===
ANTI_SPOOFING_ENABLED   = os.environ.get('ANTI_SPOOFING_ENABLED', 'False').lower() == 'true'
ANTI_SPOOFING_THRESHOLD = float(os.environ.get('ANTI_SPOOFING_THRESHOLD', 0.5))

# === KONFIGURASI FLASK ===
FLASK_HOST       = os.environ.get('FLASK_HOST', '0.0.0.0')
FLASK_PORT       = int(os.environ.get('PORT', os.environ.get('FLASK_PORT', 5000)))
FLASK_DEBUG      = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
# Jika env belum diatur (mode lokal), buat kunci acak per proses. Sesi akan
# logout setelah restart, tetapi tidak memakai kunci publik yang dapat dipalsukan.
FLASK_SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or secrets.token_urlsafe(48)

# === KONFIGURASI ESP32 ===
ESP32_ENABLED = os.environ.get('ESP32_ENABLED', 'False').lower() == 'true'
ESP32_IP      = os.environ.get('ESP32_IP', '192.168.1.100')
ESP32_PORT    = int(os.environ.get('ESP32_PORT', 80))
ESP32_TIMEOUT = int(os.environ.get('ESP32_TIMEOUT', 3))
