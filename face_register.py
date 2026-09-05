# face_register.py — Đăng ký khuôn mặt người dùng mới (Script CLI độc lập)

import cv2
import os
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from database import tambah_user, nim_sudah_ada
from config import DATASET_PATH, FOTO_PER_USER, CAMERA_INDEX

def registrasi_wajah():
    print("=" * 45)
    print("      ĐĂNG KÝ SINH VIÊN MỚI")
    print("=" * 45)

    # Nhập thông tin sinh viên
    nama = input("Nhập họ và tên sinh viên : ").strip()
    nim  = input("Nhập mã sinh viên (MSV)   : ").strip()

    if not nama or not nim:
        print("[LỖI] Họ tên và mã sinh viên không được để trống.")
        return

    if nim_sudah_ada(nim):
        print(f"[LỖI] Mã sinh viên {nim} đã tồn tại trong cơ sở dữ liệu.")
        return

    # Lưu vào database, lấy ID
    user_id = tambah_user(nama, nim)
    print(f"\n[THÔNG TIN] Đã đăng ký sinh viên với ID: {user_id}")

    # Tạo thư mục dataset cho sinh viên này
    folder_user = os.path.join(DATASET_PATH, f"{user_id}_{nama.replace(' ', '_')}")
    os.makedirs(folder_user, exist_ok=True)

    # Tải bộ phát hiện khuôn mặt Haar Cascade
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )

    cam = cv2.VideoCapture(CAMERA_INDEX)
    cam.set(3, 640)  # chiều rộng khung hình
    cam.set(4, 480)  # chiều cao khung hình

    print(f"\n[THÔNG TIN] Camera đang hoạt động. Bắt đầu chụp {FOTO_PER_USER} ảnh khuôn mặt...")
    print("[THÔNG TIN] Hướng khuôn mặt vào camera. Xoay nhẹ sang trái/phải/lên/xuống.")
    print("[THÔNG TIN] Nhấn phím 'Q' để hủy bỏ.\n")

    jumlah_foto = 0

    while jumlah_foto < FOTO_PER_USER:
        ret, frame = cam.read()
        if not ret:
            print("[LỖI] Camera không thể đọc khung hình.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.3,
            minNeighbors=5,
            minSize=(100, 100)
        )

        for (x, y, w, h) in faces:
            jumlah_foto += 1

            # Lưu ảnh khuôn mặt (grayscale, cắt crop)
            wajah_crop = gray[y:y+h, x:x+w]
            nama_file  = os.path.join(folder_user, f"{jumlah_foto}.jpg")
            cv2.imwrite(nama_file, wajah_crop)

            # Vẽ khung chữ nhật và tiến trình lên màn hình
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"Anh: {jumlah_foto}/{FOTO_PER_USER}",
                        (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 0), 2)

        status = f"Dang chup anh... {jumlah_foto}/{FOTO_PER_USER}"
        cv2.putText(frame, status, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(frame, f"Ho ten: {nama} | MSV: {nim}", (10, 460),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        cv2.imshow("Dang ky khuon mat - Nhan Q de huy", frame)

        if cv2.waitKey(100) & 0xFF == ord('q'):
            print("\n[THÔNG TIN] Đăng ký bị hủy bởi người dùng.")
            break

    cam.release()
    cv2.destroyAllWindows()

    if jumlah_foto >= FOTO_PER_USER:
        print(f"\n[THÀNH CÔNG] Đã lưu {jumlah_foto} ảnh khuôn mặt thành công.")
        print(f"[THÔNG TIN]   Thư mục lưu trữ: {folder_user}")
        print(f"[THÔNG TIN]   Chạy lệnh 'python train_model.py' để cập nhật mô hình nhận diện.\n")
    else:
        print(f"\n[CẢNH BÁO] Chỉ có {jumlah_foto} ảnh được lưu (chưa đủ {FOTO_PER_USER} ảnh theo yêu cầu).")

if __name__ == "__main__":
    registrasi_wajah()