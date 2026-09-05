# train_model.py — Huấn luyện mô hình nhận diện khuôn mặt từ tập dữ liệu

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

from PIL import Image
from config import DATASET_PATH, MODEL_PATH

def ambil_data_training(dataset_path):
    """
    Đọc tất cả ảnh từ thư mục dataset.
    Định dạng tên thư mục: {user_id}_{nama}
    Trả về: danh sách khuôn mặt (numpy array) và danh sách ID
    """
    wajah_list = []
    id_list    = []

    if not os.path.exists(dataset_path):
        print(f"[LỖI] Không tìm thấy thư mục dataset: {dataset_path}")
        return [], []

    for folder_name in os.listdir(dataset_path):
        folder_path = os.path.join(dataset_path, folder_name)
        if not os.path.isdir(folder_path):
            continue

        try:
            user_id = int(folder_name.split("_")[0])
        except ValueError:
            print(f"[BỎ QUA] Thư mục không hợp lệ: {folder_name}")
            continue

        for file_name in os.listdir(folder_path):
            if not file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue

            img_path = os.path.join(folder_path, file_name)
            try:
                img    = Image.open(img_path).convert('L')  # grayscale
                img_np = np.array(img, 'uint8')
                wajah_list.append(img_np)
                id_list.append(user_id)
            except Exception as e:
                print(f"[BỎ QUA] Không thể đọc tệp ảnh {img_path}: {e}")

    return wajah_list, id_list

def latih_model():
    print("=" * 45)
    print("   HUẤN LUYỆN MÔ HÌNH NHẬN DIỆN (LBPH)")
    print("=" * 45)

    print("\n[THÔNG TIN] Đang đọc dữ liệu ảnh khuôn mặt...")
    wajah_list, id_list = ambil_data_training(DATASET_PATH)

    if len(wajah_list) == 0:
        print("[LỖI] Không tìm thấy dữ liệu ảnh khuôn mặt nào.")
        print("[THÔNG TIN]  Vui lòng chạy lệnh 'python face_register.py' để thu thập ảnh trước.")
        return

    jumlah_user = len(set(id_list))
    print(f"[THÔNG TIN] Tổng số ảnh       : {len(wajah_list)}")
    print(f"[THÔNG TIN] Tổng số sinh viên : {jumlah_user}")
    print(f"\n[THÔNG TIN] Đang huấn luyện mô hình LBPH, vui lòng đợi...")

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(wajah_list, np.array(id_list))

    # Đảm bảo thư mục lưu trữ tồn tại
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    recognizer.write(MODEL_PATH)

    print(f"[THÀNH CÔNG] Đã lưu mô hình thành công vào: {MODEL_PATH}")
    print(f"[THÔNG TIN]   Đã huấn luyện dữ liệu cho {jumlah_user} sinh viên.")
    print(f"\n[THÔNG TIN]   Chạy lệnh 'python face_recognize.py' để bắt đầu điểm danh.\n")

if __name__ == "__main__":
    latih_model()