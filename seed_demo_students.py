# seed_demo_students.py
# Script thêm 20 dữ liệu sinh viên demo phục vụ kiểm thử hệ thống điểm danh
# Hỗ trợ chèn thông tin và ảnh mẫu (test thumbnail) cho từng sinh viên.

import os
import sys
import shutil

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import database as db
from config import DATASET_PATH

# 20 sinh viên demo chuẩn tiếng Việt và mã sinh viên TMU
DEMO_STUDENTS = [
    {"stt": 1,  "nama": "Nguyễn Văn An",      "nim": "22D190001"},
    {"stt": 2,  "nama": "Trần Thị Mai Anh",   "nim": "22D190002"},
    {"stt": 3,  "nama": "Lê Hoàng Bảo",       "nim": "22D190003"},
    {"stt": 4,  "nama": "Phạm Quốc Cường",    "nim": "22D190004"},
    {"stt": 5,  "nama": "Đỗ Thùy Dung",       "nim": "22D190005"},
    {"stt": 6,  "nama": "Hoàng Minh Đức",     "nim": "22D190006"},
    {"stt": 7,  "nama": "Vũ Khánh Huyền",     "nim": "22D190007"},
    {"stt": 8,  "nama": "Đặng Gia Huy",       "nim": "22D190008"},
    {"stt": 9,  "nama": "Bùi Quang Khải",     "nim": "22D190009"},
    {"stt": 10, "nama": "Ngô Bảo Linh",       "nim": "22D190010"},
    {"stt": 11, "nama": "Dương Đức Long",     "nim": "22D190011"},
    {"stt": 12, "nama": "Hồ Phương Nga",      "nim": "22D190012"},
    {"stt": 13, "nama": "Lý Trọng Nhân",      "nim": "22D190013"},
    {"stt": 14, "nama": "Mai Tuấn Phong",     "nim": "22D190014"},
    {"stt": 15, "nama": "Đoàn Hồng Phúc",     "nim": "22D190015"},
    {"stt": 16, "nama": "Trịnh Thanh Thảo",   "nim": "22D190016"},
    {"stt": 17, "nama": "Võ Minh Trí",        "nim": "22D190017"},
    {"stt": 18, "nama": "Đinh Hoài Thương",   "nim": "22D190018"},
    {"stt": 19, "nama": "Chu Tấn Phát",       "nim": "22D190019"},
    {"stt": 20, "nama": "Hà Yến Vy",          "nim": "22D190020"}
]

def get_sample_photo_bytes():
    """Tìm một ảnh mẫu có sẵn trong dataset để làm ảnh test cho sinh viên demo."""
    candidates = [
        os.path.join(DATASET_PATH, '209', '00_center.jpg'),
        os.path.join(DATASET_PATH, '191', '05_center.jpg'),
    ]
    for c in candidates:
        if os.path.isfile(c):
            with open(c, 'rb') as f:
                return f.read()
    
    # Nếu không tìm thấy, thử tìm bất kỳ file jpg nào trong dataset
    for root, _, files in os.walk(DATASET_PATH):
        for f in files:
            if f.lower().endswith('.jpg'):
                with open(os.path.join(root, f), 'rb') as img_f:
                    return img_f.read()
    return None

def clean_demo_data():
    """Xóa các sinh viên demo có mã 22D1900xx để dễ dàng reset dữ liệu."""
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nim, nama FROM users WHERE nim LIKE '22D1900%'")
    demo_users = cursor.fetchall()
    print(f"[*] Tìm thấy {len(demo_users)} sinh viên demo cần dọn dẹp...")
    
    for u in demo_users:
        u_id = u['id']
        # Xóa folder dataset
        u_folder = os.path.join(DATASET_PATH, str(u_id))
        if os.path.exists(u_folder):
            shutil.rmtree(u_folder, ignore_errors=True)
        # Xóa khỏi database
        db.hapus_user(u_id)
        print(f"  - Đã xóa sinh viên: {u['nama']} (NIM: {u['nim']}, ID: {u_id})")
    
    cursor.close()
    conn.close()
    print("[✓] Hoàn tất dọn dẹp dữ liệu demo.")

def seed_students():
    """Thêm 20 sinh viên demo vào lớp học hiện có."""
    # 1. Tìm lớp học
    classes = db.get_semua_kelas()
    if not classes:
        print("[!] Không tìm thấy lớp học nào trong hệ thống. Vui lòng tạo lớp trước.")
        return
    
    target_class = classes[0]
    kelas_id = target_class['id']
    kelas_nama = target_class['nama_kelas']
    print(f"[*] Sử dụng lớp học mục tiêu: ID {kelas_id} - '{kelas_nama}'")

    sample_img = get_sample_photo_bytes()
    if sample_img:
        print(f"[✓] Đã tải ảnh mẫu kiểm thử ({len(sample_img)} bytes).")
    else:
        print("[!] Cảnh báo: Không tìm thấy ảnh mẫu nào trong dataset.")

    added_count = 0
    skipped_count = 0

    for s in DEMO_STUDENTS:
        # Kiểm tra nếu NIM đã có
        if db.nim_sudah_ada(s['nim']):
            print(f"[-] Sinh viên {s['nama']} ({s['nim']}) đã tồn tại. Bỏ qua.")
            skipped_count += 1
            continue

        user_id = db.tambah_user(
            nama=s['nama'],
            nim=s['nim'],
            kelas_id=kelas_id,
            stt=s['stt']
        )

        if user_id:
            # Tạo thư mục ảnh dataset và chèn ảnh test nếu có
            if sample_img:
                user_folder = os.path.join(DATASET_PATH, str(user_id))
                os.makedirs(user_folder, exist_ok=True)
                sample_path = os.path.join(user_folder, '00_sample.jpg')
                with open(sample_path, 'wb') as img_out:
                    img_out.write(sample_img)

            print(f"[+] Thêm thành công: ID {user_id:3d} | STT {s['stt']:2d} | {s['nama']:<22} | NIM: {s['nim']}")
            added_count += 1
        else:
            print(f"[!] Lỗi khi thêm: {s['nama']} ({s['nim']})")

    print(f"\n=======================================================")
    print(f"Tổng kết: Đã thêm mới {added_count} sinh viên, bỏ qua {skipped_count} sinh viên.")
    print(f"Lớp: {kelas_nama} (ID: {kelas_id})")
    print(f"=======================================================")

def seed_attendance_records():
    """Tạo bản ghi điểm danh cho toàn bộ sinh viên của lớp mục tiêu (ML - 02)."""
    classes = db.get_semua_kelas()
    if not classes:
        print("[!] Không tìm thấy lớp học.")
        return
    kelas_id = classes[0]['id']
    kelas_nama = classes[0]['nama_kelas']
    
    # Tìm lịch học tương ứng
    schedules = db.get_semua_jadwal()
    target_jadwal = None
    for j in schedules:
        if j.get('kelas_id') == kelas_id or j.get('nama_kelas') == kelas_nama:
            target_jadwal = j
            break
    if not target_jadwal and schedules:
        target_jadwal = schedules[0]
    
    if not target_jadwal:
        print("[!] Không tìm thấy lịch học nào cho lớp.")
        return
        
    jadwal_id = target_jadwal['id']
    students = db.get_users_by_kelas(kelas_id)
    print(f"[*] Nạp bản ghi điểm danh cho {len(students)} sinh viên lớp {kelas_nama} (Jadwal ID {jadwal_id})...")
    
    from datetime import date
    today = date.today()
    
    count = 0
    for idx, s in enumerate(students):
        user_id = s['id']
        minute = 15 + (idx % 25)
        second = (idx * 7) % 60
        waktu = f"06:{minute:02d}:{second:02d}"
        status = 'hadir' if minute <= 30 else 'terlambat'
        
        res = db.catat_absensi(
            user_id=user_id,
            jadwal_id=jadwal_id,
            tanggal=today,
            waktu_absen=waktu,
            status=status,
            dibuat_manual=True
        )
        if res:
            count += 1
    print(f"[✓] Đã tạo thành công {count} bản ghi điểm danh cho ngày {today}.")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ('--clean', '-c', 'clean'):
        clean_demo_data()
    else:
        seed_students()
        seed_attendance_records()

