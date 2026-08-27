# face/anti_spoofing.py — Deteksi wajah asli vs foto/spoofing
# Metode: Texture Analysis menggunakan Local Binary Pattern (LBP)
# Threshold: score > 0.7 = wajah asli, score <= 0.7 = foto/spoofing

import cv2
import numpy as np
from config import ANTI_SPOOFING_THRESHOLD, ANTI_SPOOFING_ENABLED
from face.cascade import create_frontal_face_cascade


def _compute_lbp(image, radius=1, neighbors=8):
    """Hitung Local Binary Pattern secara manual.
    
    LBP menganalisis tekstur mikro pada gambar — wajah asli memiliki
    variasi tekstur yang lebih kaya dibanding foto cetakan/layar.
    
    Args:
        image: gambar grayscale (numpy array)
        radius: radius lingkaran LBP
        neighbors: jumlah titik sampling di sekitar center pixel
    
    Returns:
        numpy array berisi nilai LBP per pixel
    """
    rows, cols = image.shape
    lbp = np.zeros_like(image, dtype=np.uint8)

    for i in range(radius, rows - radius):
        for j in range(radius, cols - radius):
            center = image[i, j]
            binary_string = 0

            # Sampling 8 titik di sekitar pixel center
            # Urutan: atas, atas-kanan, kanan, bawah-kanan, bawah, bawah-kiri, kiri, atas-kiri
            offsets = [
                (-1, 0), (-1, 1), (0, 1), (1, 1),
                (1, 0), (1, -1), (0, -1), (-1, -1)
            ]

            for bit, (dy, dx) in enumerate(offsets):
                neighbor_val = image[i + dy, j + dx]
                if neighbor_val >= center:
                    binary_string |= (1 << bit)

            lbp[i, j] = binary_string

    return lbp


def _compute_lbp_fast(image):
    """Versi cepat LBP menggunakan operasi numpy (tanpa loop Python).
    
    Jauh lebih cepat dari _compute_lbp untuk frame real-time.
    """
    rows, cols = image.shape
    # Padding agar tidak perlu boundary check
    padded = np.pad(image.astype(np.int16), 1, mode='reflect')
    center = padded[1:-1, 1:-1]

    # 8 arah neighbor
    neighbors = [
        padded[0:-2, 1:-1],  # atas
        padded[0:-2, 2:],    # atas-kanan
        padded[1:-1, 2:],    # kanan
        padded[2:,   2:],    # bawah-kanan
        padded[2:,   1:-1],  # bawah
        padded[2:,   0:-2],  # bawah-kiri
        padded[1:-1, 0:-2],  # kiri
        padded[0:-2, 0:-2],  # atas-kiri
    ]

    lbp = np.zeros((rows, cols), dtype=np.uint8)
    for bit, neighbor in enumerate(neighbors):
        lbp |= ((neighbor >= center).astype(np.uint8) << bit)

    return lbp


def _analyze_texture(lbp_image):
    """Analisis histogram LBP untuk menentukan score keaslian.
    
    Wajah asli → histogram LBP memiliki distribusi yang lebih merata
    (varian tinggi) karena tekstur kulit 3D memiliki variasi pencahayaan.
    
    Foto/layar → histogram LBP cenderung lebih seragam (varian rendah)
    karena pencetakan/layar menghaluskan detail mikro.
    
    Returns:
        float score 0.0 - 1.0 (lebih tinggi = lebih mungkin asli)
    """
    # Hitung histogram LBP (256 bin untuk 8-bit LBP)
    hist = cv2.calcHist([lbp_image], [0], None, [256], [0, 256])
    hist = hist.flatten()

    # Normalisasi histogram
    hist = hist / (hist.sum() + 1e-7)

    # Metrik 1: Entropy — mengukur keacakan distribusi
    # Wajah asli punya entropy lebih tinggi
    entropy = -np.sum(hist * np.log2(hist + 1e-7))
    max_entropy = np.log2(256)  # Entropy maksimum (distribusi merata sempurna)
    entropy_score = entropy / max_entropy

    # Metrik 2: Standar deviasi histogram — variasi tekstur
    hist_std = np.std(hist)
    # Normalisasi ke range 0-1 (berdasarkan observasi empiris)
    std_score = min(hist_std * 50, 1.0)

    # Metrik 3: Jumlah bin non-zero — kekayaan tekstur
    non_zero_ratio = np.count_nonzero(hist) / 256.0

    # Gabungkan dengan bobot
    # Entropy paling penting, diikuti kekayaan tekstur, lalu variasi
    combined_score = (
        0.45 * entropy_score +
        0.30 * non_zero_ratio +
        0.25 * std_score
    )

    return round(combined_score, 4)


def _disabled_result():
    return {
        'is_real': True,
        'score': 1.0,
        'threshold': ANTI_SPOOFING_THRESHOLD,
        'label': 'REAL (bypass)'
    }


def _no_face_result():
    return {
        'is_real': False,
        'score': 0.0,
        'threshold': ANTI_SPOOFING_THRESHOLD,
        'label': 'NO_FACE'
    }


def _analyze_face_roi(face_roi):
    """Chấm anti-spoofing cho đúng một vùng khuôn mặt đã được phát hiện."""
    if face_roi is None or face_roi.size == 0:
        return _no_face_result()
    if len(face_roi.shape) == 3:
        face_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    face_roi = cv2.resize(face_roi, (200, 200))

    lbp_full = _compute_lbp_fast(face_roi)
    score_full = _analyze_texture(lbp_full)

    blurred = cv2.GaussianBlur(face_roi, (3, 3), 0)
    lbp_blur = _compute_lbp_fast(blurred)
    score_blur = _analyze_texture(lbp_blur)

    laplacian_var = cv2.Laplacian(face_roi, cv2.CV_64F).var()
    sharpness_score = min(laplacian_var / 500.0, 1.0)
    final_score = (
        0.40 * score_full +
        0.30 * score_blur +
        0.30 * sharpness_score
    )

    is_real = final_score > ANTI_SPOOFING_THRESHOLD
    return {
        'is_real': is_real,
        'score': round(final_score, 4),
        'threshold': ANTI_SPOOFING_THRESHOLD,
        'label': 'REAL' if is_real else 'SPOOFING',
        'detail': {
            'texture_score': score_full,
            'blur_texture_score': score_blur,
            'sharpness_score': round(sharpness_score, 4),
        }
    }


def check_face(frame, bbox):
    """Cek anti-spoofing riêng cho một bbox `(x, y, w, h)` trong frame."""
    if not ANTI_SPOOFING_ENABLED:
        return _disabled_result()
    if frame is None or bbox is None or len(bbox) != 4:
        return _no_face_result()

    x, y, w, h = (int(value) for value in bbox)
    frame_height, frame_width = frame.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(frame_width, x + w), min(frame_height, y + h)
    if x1 <= x0 or y1 <= y0:
        return _no_face_result()
    return _analyze_face_roi(frame[y0:y1, x0:x1])


def check(frame):
    """Cek apakah wajah dalam frame adalah wajah asli atau foto/spoofing.
    
    Args:
        frame: numpy array BGR dari OpenCV
    
    Returns:
        dict {
            'is_real': bool,     # True jika wajah asli
            'score': float,      # Score keaslian (0.0 - 1.0)
            'threshold': float,  # Threshold yang dipakai
            'label': str         # 'REAL' atau 'SPOOFING'
        }
    """
    # Konversi ke grayscale
    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame.copy()

    # Jika anti-spoofing dinonaktifkan via config, langsung REAL
    if not ANTI_SPOOFING_ENABLED:
        return {
            'is_real': True,
            'score': 1.0,
            'threshold': ANTI_SPOOFING_THRESHOLD,
            'label': 'REAL (bypass)'
        }

    # Deteksi wajah terlebih dahulu
    cascade = create_frontal_face_cascade()
    faces = cascade.detectMultiScale(gray, 1.3, 5, minSize=(80, 80))

    if len(faces) == 0:
        return {
            'is_real': False,
            'score': 0.0,
            'threshold': ANTI_SPOOFING_THRESHOLD,
            'label': 'NO_FACE'
        }

    # Ambil wajah terbesar (terdekat ke kamera)
    areas = [w * h for (x, y, w, h) in faces]
    idx = np.argmax(areas)
    (x, y, w, h) = faces[idx]

    # Crop area wajah
    face_roi = gray[y:y+h, x:x+w]

    # Resize untuk konsistensi analisis
    face_roi = cv2.resize(face_roi, (200, 200))

    # --- Analisis multi-skala untuk ketahanan lebih baik ---

    # Skala 1: full-size
    lbp_full = _compute_lbp_fast(face_roi)
    score_full = _analyze_texture(lbp_full)

    # Skala 2: Gaussian blur ringan (simulasi depth-of-field)
    blurred = cv2.GaussianBlur(face_roi, (3, 3), 0)
    lbp_blur = _compute_lbp_fast(blurred)
    score_blur = _analyze_texture(lbp_blur)

    # Skala 3: Analisis gradien (Laplacian variance) — ukuran ketajaman
    laplacian_var = cv2.Laplacian(face_roi, cv2.CV_64F).var()
    # Normalisasi: wajah asli umumnya punya laplacian > 100
    sharpness_score = min(laplacian_var / 500.0, 1.0)

    # Gabungkan semua score
    final_score = (
        0.40 * score_full +
        0.30 * score_blur +
        0.30 * sharpness_score
    )

    is_real = final_score > ANTI_SPOOFING_THRESHOLD

    return {
        'is_real': is_real,
        'score': round(final_score, 4),
        'threshold': ANTI_SPOOFING_THRESHOLD,
        'label': 'REAL' if is_real else 'SPOOFING',
        'detail': {
            'texture_score': score_full,
            'blur_texture_score': score_blur,
            'sharpness_score': round(sharpness_score, 4),
        }
    }


def check_frame_quick(frame):
    """Versi ringkas — return True jika wajah asli, False jika spoofing.
    Dipakai di alur absensi otomatis untuk pengecekan cepat.
    """
    result = check(frame)
    return result['is_real']
