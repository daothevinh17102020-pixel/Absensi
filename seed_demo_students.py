# seed_demo_students.py
# Script thêm 20 dữ liệu sinh viên demo và 5 buổi điểm danh phục vụ kiểm thử hệ thống điểm danh
# Hỗ trợ chèn thông tin, ảnh mẫu (test thumbnail) và phân bổ 5 buổi điểm danh đa dạng trạng thái.

import os
import sys
import shutil
from datetime import date, timedelta

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
    {"stt": 7,  "nama": "Vũ Thị Hà",          "nim": "22D190007"},
    {"stt": 8,  "nama": "Nguyễn Quang Huy",    "nim": "22D190008"},
    {"stt": 9,  "nama": "Đặng Thu Hương",     "nim": "22D190009"},
    {"stt": 10, "nama": "Bùi Tuấn Kiệt",      "nim": "22D190010"},
    {"stt": 11, "nama": "Phan Thanh Mai",     "nim": "22D190011"},
    {"stt": 12, "nama": "Đinh Trọng Nam",      "nim": "22D190012"},
    {"stt": 13, "nama": "Ngô Quỳnh Nga",      "nim": "22D190013"},
    {"stt": 14, "nama": "Lý Hồng Phong",      "nim": "22D190014"},
    {"stt": 15, "nama": "Trịnh Minh Quân",    "nim": "22D190015"},
    {"stt": 16, "nama": "Mai Như Quỳnh",      "nim": "22D190016"},
    {"stt": 17, "nama": "Tạ Thị Thảo",        "nim": "22D190017"},
    {"stt": 18, "nama": "Dương Văn Tiến",     "nim": "22D190018"},
    {"stt": 19, "nama": "Đào Minh Tuấn",      "nim": "22D190019"},
    {"stt": 20, "nama": "Cao Phương Uyên",    "nim": "22D190020"}
]

# 5 ngày học của 5 buổi (mỗi buổi cách nhau 1 tuần)
SESSION_DATES = {
    1: date(2026, 8, 8),
    2: date(2026, 8, 15),
    3: date(2026, 8, 22),
    4: date(2026, 8, 29),
    5: date(2026, 9, 5)
}

# Kịch bản 5 buổi học chi tiết cho từng sinh viên (đáp ứng đầy đủ case Cấm thi, Cảnh báo, Đủ ĐK thi)
STUDENT_SESSIONS_SCENARIOS = {
    "22D190001": {1: "hadir", 2: "hadir", 3: "hadir", 4: "hadir", 5: "terlambat"}, # An: Muộn buổi 5
    "22D190002": {1: "hadir", 2: "hadir", 3: "hadir", 4: "hadir", 5: "hadir"},     # Mai Anh: Đủ 100%
    "22D190003": {1: "hadir", 2: "hadir", 3: "hadir", 4: "hadir", 5: "hadir"},     # Bảo: Đủ 100%
    "22D190004": {1: "hadir", 2: "terlambat", 3: "hadir", 4: "hadir", 5: "hadir"}, # Cường: Muộn buổi 2
    "22D190005": {1: "hadir", 2: "alpha", 3: "alpha", 4: "hadir", 5: "izin"},      # Dung: 1 phép + 2 vắng = 3 buổi -> CẢNH BÁO (3B)
    "22D190006": {1: "alpha", 2: "alpha", 3: "terlambat", 4: "alpha", 5: "alpha"}, # Đức: 4 vắng -> CẤM THI (4B)
    "22D190007": {1: "hadir", 2: "hadir", 3: "hadir", 4: "hadir", 5: "hadir"},     # Hà: Đủ 100%
    "22D190008": {1: "hadir", 2: "hadir", 3: "hadir", 4: "terlambat", 5: "hadir"}, # Huy: Muộn buổi 4
    "22D190009": {1: "hadir", 2: "hadir", 3: "hadir", 4: "hadir", 5: "hadir"},     # Hương: Đủ 100%
    "22D190010": {1: "hadir", 2: "hadir", 3: "hadir", 4: "hadir", 5: "hadir"},     # Kiệt: Đủ 100%
    "22D190011": {1: "izin", 2: "hadir", 3: "hadir", 4: "hadir", 5: "hadir"},      # Mai: Phép buổi 1
    "22D190012": {1: "hadir", 2: "hadir", 3: "hadir", 4: "hadir", 5: "hadir"},     # Nam: Đủ 100%
    "22D190013": {1: "hadir", 2: "hadir", 3: "hadir", 4: "hadir", 5: "hadir"},     # Nga: Đủ 100%
    "22D190014": {1: "terlambat", 2: "hadir", 3: "hadir", 4: "hadir", 5: "hadir"}, # Phong: Muộn buổi 1
    "22D190015": {1: "hadir", 2: "hadir", 3: "hadir", 4: "hadir", 5: "hadir"},     # Quân: Đủ 100%
    "22D190016": {1: "hadir", 2: "hadir", 3: "terlambat", 4: "hadir", 5: "hadir"}, # Quỳnh: Muộn buổi 3
    "22D190017": {1: "hadir", 2: "hadir", 3: "hadir", 4: "hadir", 5: "hadir"},     # Thảo: Đủ 100%
    "22D190018": {1: "hadir", 2: "hadir", 3: "alpha", 4: "hadir", 5: "hadir"},     # Tiến: Vắng buổi 3
    "22D190019": {1: "hadir", 2: "hadir", 3: "hadir", 4: "hadir", 5: "hadir"},     # Tuấn: Đủ 100%
    "22D190020": {1: "hadir", 2: "hadir", 3: "hadir", 4: "hadir", 5: "hadir"}      # Uyên: Đủ 100%
}

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

def seed_students_and_attendance():
    """Thêm 20 sinh viên demo và nạp đầy đủ 5 buổi dữ liệu điểm danh."""
    # 1. Tìm lớp học
    classes = db.get_semua_kelas()
    if not classes:
        print("[!] Không tìm thấy lớp học nào. Đang tạo lớp mới 'ML - 02'...")
        kelas_id = db.tambah_kelas('ML - 02', '2025', 1)
        kelas_nama = 'ML - 02'
    else:
        target_class = classes[0]
        kelas_id = target_class['id']
        kelas_nama = target_class['nama_kelas']
    print(f"[*] Sử dụng lớp học mục tiêu: ID {kelas_id} - '{kelas_nama}'")

    # 2. Tìm lịch học
    schedules = db.get_semua_jadwal()
    target_jadwal = None
    for j in schedules:
        if j.get('kelas_id') == kelas_id or j.get('nama_kelas') == kelas_nama:
            target_jadwal = j
            break
    if not target_jadwal and schedules:
        target_jadwal = schedules[0]
    
    if not target_jadwal:
        print("[!] Chưa có lịch học, đang tạo lịch học mới cho lớp...")
        # Tìm môn học
        mks = db.get_semua_matakuliah()
        mk_id = mks[0]['id'] if mks else db.tambah_matakuliah('Machine Learning', 'ML01')
        jadwal_id = db.tambah_jadwal(kelas_id, mk_id, 'Thứ Sáu', '06:30', '11:30', '07:00')
    else:
        jadwal_id = target_jadwal['id']

    print(f"[*] Sử dụng lịch học mục tiêu: ID {jadwal_id}")

    sample_img = get_sample_photo_bytes()
    if sample_img:
        print(f"[✓] Đã tải ảnh mẫu kiểm thử ({len(sample_img)} bytes).")

    user_id_map = {}
    added_count = 0

    # 3. Thêm 20 sinh viên
    for s in DEMO_STUDENTS:
        existing = db.get_user_by_nim(s['nim'])
        if existing:
            user_id = existing['id']
            # Cập nhật lớp học nếu chưa đúng
            db.update_user(user_id, s['nama'], s['nim'], kelas_id, s['stt'])
        else:
            user_id = db.tambah_user(
                nama=s['nama'],
                nim=s['nim'],
                kelas_id=kelas_id,
                stt=s['stt']
            )
            added_count += 1

        user_id_map[s['nim']] = user_id

        # Tạo folder dataset
        if sample_img and user_id:
            user_folder = os.path.join(DATASET_PATH, str(user_id))
            os.makedirs(user_folder, exist_ok=True)
            sample_path = os.path.join(user_folder, '00_sample.jpg')
            if not os.path.exists(sample_path):
                with open(sample_path, 'wb') as img_out:
                    img_out.write(sample_img)

    print(f"[✓] Đã sẵn sàng 20 sinh viên trong database (Mới tạo: {added_count}).")

    # 4. Nạp dữ liệu 5 buổi điểm danh
    print(f"[*] Tiến hành nạp dữ liệu 5 buổi điểm danh cho 20 sinh viên...")
    attendance_count = 0

    for nim, user_id in user_id_map.items():
        scenarios = STUDENT_SESSIONS_SCENARIOS.get(nim, {1: "hadir", 2: "hadir", 3: "hadir", 4: "hadir", 5: "hadir"})
        
        for buoi in range(1, 6):
            tgl = SESSION_DATES[buoi]
            status = scenarios.get(buoi, "hadir")
            
            # Thời gian điểm danh
            if status == "hadir":
                waktu = "06:45:00"
                alasan = None
            elif status == "terlambat":
                waktu = "07:15:00"
                alasan = "Đến lớp sau hạn muộn"
            elif status == "izin":
                waktu = None
                alasan = "Có đơn xin phép: Sốt xuất huyết nằm viện" if nim == "22D190005" else "Trùng lịch thi tin học"
            else: # alpha
                waktu = None
                alasan = "Vắng không phép"

            res = db.catat_absensi(
                user_id=user_id,
                jadwal_id=jadwal_id,
                tanggal=tgl,
                waktu_absen=waktu,
                status=status,
                buoi_so=buoi,
                alasan=alasan,
                dibuat_manual=True
            )
            if res:
                attendance_count += 1

    print(f"[✓] Nạp thành công {attendance_count} bản ghi điểm danh qua 5 buổi học!")
    print(f"=======================================================")
    print(f"KẾT QUẢ ĐỒNG NHẤT:")
    print(f"- Lớp: {kelas_nama} (ID: {kelas_id})")
    print(f"- Lịch học ca: ID {jadwal_id}")
    print(f"- Số sinh viên: 20 sinh viên (NIM: 22D190001 -> 22D190020)")
    print(f"- Số buổi học đã điểm danh: 5 Buổi (Buổi 1 -> Buổi 5)")
    print(f"- Sinh viên cảnh báo (3B): Đỗ Thùy Dung (22D190005)")
    print(f"- Sinh viên cấm thi (4B): Hoàng Minh Đức (22D190006)")
    print(f"=======================================================")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ('--clean', '-c', 'clean'):
        clean_demo_data()
    else:
        seed_students_and_attendance()
