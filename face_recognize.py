# face_recognize.py — Nhận diện khuôn mặt thời gian thực + Tích hợp ESP32 (Script CLI)

import cv2
import numpy as np
import os
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import requests
from database import get_user_by_id, catat_absensi
from config import (MODEL_PATH, CONFIDENCE_THRESHOLD, CAMERA_INDEX,
                    FLASK_PORT, ESP32_ENABLED, ESP32_IP, ESP32_PORT, ESP32_TIMEOUT)

def kirim_notifikasi(nama, nim, status):
    """
    Gửi kết quả điểm danh tới:
    1. Flask server (để cập nhật giao diện dashboard thời gian thực)
    2. ESP32 (hiển thị LCD & đèn LED) — chỉ kích hoạt nếu ESP32_ENABLED = True
    """
    payload = {"nama": nama, "nim": nim, "status": status}

    # -- Gửi tới Flask dashboard --
    try:
        requests.post(
            f"http://127.0.0.1:{FLASK_PORT}/api/hasil-absensi",
            json=payload,
            timeout=2
        )
    except Exception:
        pass  # Flask có thể chưa chạy, không gây lỗi ngắt quãng

    # -- Gửi tới ESP32 (nếu được kích hoạt) --
    if ESP32_ENABLED:
        try:
            resp = requests.post(
                f"http://{ESP32_IP}:{ESP32_PORT}/absensi",
                json=payload,
                timeout=ESP32_TIMEOUT
            )
            if resp.status_code == 200:
                print(f"[ESP32] Đã gửi thông báo → {status}")
            else:
                print(f"[ESP32] Phản hồi bất thường: {resp.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"[CẢNH BÁO] Không thể kết nối tới ESP32 tại {ESP32_IP}:{ESP32_PORT}")
        except requests.exceptions.Timeout:
            print(f"[CẢNH BÁO] ESP32 timeout sau {ESP32_TIMEOUT}s")
        except Exception as e:
            print(f"[CẢNH BÁO] Gửi tín hiệu tới ESP32 thất bại: {e}")

def cek_esp32():
    """Kiểm tra ping ESP32 trước khi bắt đầu nhận diện."""
    if not ESP32_ENABLED:
        print("[THÔNG TIN] ESP32 đang tắt (ESP32_ENABLED = False trong config.py)")
        return
    try:
        resp = requests.get(
            f"http://{ESP32_IP}:{ESP32_PORT}/ping",
            timeout=ESP32_TIMEOUT
        )
        if resp.status_code == 200:
            print(f"[OK] ESP32 đã kết nối tại {ESP32_IP}:{ESP32_PORT}")
        else:
            print(f"[CẢNH BÁO] ESP32 phản hồi trạng thái: {resp.status_code}")
    except Exception:
        print(f"[CẢNH BÁO] Không thể kết nối tới ESP32 tại {ESP32_IP} — Vui lòng kiểm tra:")
        print("       1. ESP32 đã cấp nguồn và kết nối WiFi")
        print("       2. Địa chỉ IP trong config.py chính xác")
        print("       3. Máy tính và ESP32 đang chung một mạng nội bộ")

def mulai_pengenalan():
    print("=" * 50)
    print("   HỆ THỐNG ĐIỂM DANH NHẬN DIỆN KHUÔN MẶT")
    print("=" * 50)

    # Kiểm tra mô hình khả dụng
    if not os.path.exists(MODEL_PATH):
        print(f"[LỖI] Không tìm thấy tệp mô hình: {MODEL_PATH}")
        print("[THÔNG TIN] Vui lòng chạy lệnh 'python train_model.py' trước.")
        return

    # Kiểm tra kết nối ESP32
    cek_esp32()

    # Tải mô hình LBPH
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(MODEL_PATH)
    print(f"[OK] Đã tải mô hình LBPH từ: {MODEL_PATH}")

    # Tải bộ phát hiện khuôn mặt Haar Cascade
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )

    cam = cv2.VideoCapture(CAMERA_INDEX)
    cam.set(3, 640)
    cam.set(4, 480)

    if not cam.isOpened():
        print("[LỖI] Không thể mở camera.")
        return

    print("\n[THÔNG TIN] Camera đang hoạt động. Hãy hướng khuôn mặt vào ống kính.")
    print(f"[THÔNG TIN] Ngưỡng nhận diện (Confidence): {CONFIDENCE_THRESHOLD}")
    print(f"[THÔNG TIN] ESP32: {'BẬT (' + ESP32_IP + ')' if ESP32_ENABLED else 'TẮT'}")
    print("[THÔNG TIN] Nhấn phím 'Q' để thoát.\n")

    # Cooldown: tránh ghi nhận điểm danh liên tục trong thời gian ngắn
    cooldown       = {}      # {user_id: frame_counter}
    COOLDOWN_FRAME = 60      # ~2 giây ở tốc độ 30fps
    frame_count    = 0

    # Tải mapping nhãn từ file
    label_map_path = MODEL_PATH.replace('.yml', '_labels.npy')
    id_map_path = MODEL_PATH.replace('.yml', '_ids.npy')
    
    label_to_user_id = {}
    if os.path.exists(label_map_path) and os.path.exists(id_map_path):
        labels = np.load(label_map_path, allow_pickle=True).item()
        ids = np.load(id_map_path, allow_pickle=True).item()
        for folder, label_num in labels.items():
            label_to_user_id[label_num] = ids[folder]
        print(f"[OK] Đã tải ánh xạ nhãn: {label_to_user_id}")
    else:
        print("[CẢNH BÁO] Không tìm thấy file ánh xạ nhãn. Dự đoán trực tiếp theo ID.")

    while True:
        ret, frame = cam.read()
        if not ret:
            print("[LỖI] Camera dừng truyền khung hình.")
            break

        frame_count += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.3,
            minNeighbors=5,
            minSize=(100, 100)
        )

        for (x, y, w, h) in faces:
            wajah_roi = gray[y:y+h, x:x+w]

            # Dự đoán danh tính
            label_pred, confidence = recognizer.predict(wajah_roi)
            user_id = label_to_user_id.get(label_pred, label_pred)

            if confidence < CONFIDENCE_THRESHOLD:
                # ── KHUÔN MẶT ĐƯỢC NHẬN DIỆN ──────────────────────────
                user = get_user_by_id(user_id)
                
                if user and confidence < CONFIDENCE_THRESHOLD:
                    nama = user['nama']
                    nim  = user['nim']

                    # Kiểm tra cooldown
                    if frame_count > cooldown.get(user_id, 0):
                        berhasil = catat_absensi(user_id, nama, nim)
                        cooldown[user_id] = frame_count + COOLDOWN_FRAME

                        if berhasil:
                            print(f"[ĐIỂM DANH] {nama} | {nim} — ĐÃ GHI NHẬN THÀNH CÔNG")
                            kirim_notifikasi(nama, nim, "berhasil")
                        else:
                            print(f"[THÔNG TIN]  {nama} đã điểm danh hôm nay.")
                            kirim_notifikasi(nama, nim, "duplikat")

                    # Khung XANH LÁ
                    label = f"{nama} ({confidence:.0f})"
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 200, 0), 2)
                    cv2.rectangle(frame, (x, y-35), (x+w, y), (0, 200, 0), -1)
                    cv2.putText(frame, label, (x+5, y-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                else:
                    # Không tìm thấy sinh viên trong CSDL
                    label = f"ID {user_id} chua dang ky ({confidence:.0f})"
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 165, 255), 2)
                    cv2.rectangle(frame, (x, y-35), (x+w, y), (0, 165, 255), -1)
                    cv2.putText(frame, label, (x+5, y-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            else:
                # ── KHÔNG NHẬN DIỆN ĐƯỢC ─────────────────────
                label = f"Khong nhan dien ({confidence:.0f})"
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 200), 2)
                cv2.rectangle(frame, (x, y-35), (x+w, y), (0, 0, 200), -1)
                cv2.putText(frame, label, (x+5, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Thông tin hiển thị trên khung hình
        esp32_status = f"ESP32: {'BAT ' + ESP32_IP if ESP32_ENABLED else 'TAT'}"
        cv2.putText(frame, "He thong diem danh khuon mat",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 0), 2)
        cv2.putText(frame, esp32_status,
                    (10, 455), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)
        cv2.putText(frame, "Nhan Q de thoat",
                    (10, 472), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)

        cv2.imshow("Diem danh - Nhan dien khuon mat", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\n[THÔNG TIN] Hệ thống đã được dừng bởi người dùng.")
            break

    cam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    mulai_pengenalan()