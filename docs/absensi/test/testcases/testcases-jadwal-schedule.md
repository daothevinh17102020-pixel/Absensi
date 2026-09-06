# Bộ Ca Kiểm Thử Nghiệp Vụ Lịch Học & Khắc Phục Lỗi Khóa Ngoại (Bug Schedule Foreign Key)

> **Phạm vi kiểm thử:** Nghiệp vụ Thêm / Sửa lịch học (`/jadwal/tambah`, `/jadwal/edit/<id>`) trong bối cảnh chuẩn hóa mô hình đào tạo TMU (1 Lớp học phần = 1 Môn học).  
> **Traceability:** Bám sát 1:1 theo Checklist [checklist-jadwal-schedule.md](../checklist/checklist-jadwal-schedule.md).

---

## Danh Sách Ca Kiểm Thử Chi Tiết (Test Cases)

| Mã TC | Ref Checklist | Độ ưu tiên | Tiền điều kiện / Dữ liệu kiểm thử | Thao tác thực hiện (Action Steps) | Kết quả mong đợi (Expected Results) | Tự động hóa |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: |
| **TC-SCH-001** | CHK-SCH-001 | **P0 (Blocker)** | Lớp `ML - 01` (id: 7) vừa tạo, chưa có bản ghi trong bảng `matakuliah`. | 1. Mở trang `/jadwal/tambah`<br>2. Chọn Lớp: `ML - 01 (Khóa K60)`<br>3. Chọn Thứ: `Chủ Nhật`<br>4. Giờ bắt đầu: `06:00`, Kết thúc: `23:00`<br>5. Hạn đi muộn: `06:15`, Buổi bắt đầu: `5`<br>6. Bấm "Lưu lịch học" | Hệ thống tự động khởi tạo môn học mặc định cho lớp (nếu chưa có), không bị lỗi khóa ngoại `1452 IntegrityError`, lưu lịch học thành công, hiển thị flash message *"Thêm lịch học thành công!"* và chuyển hướng về `/jadwal`. | Có (Unit & Integration) |
| **TC-SCH-002** | CHK-SCH-002 | **P1 (High)** | Lớp `ML - 02` đã có sẵn môn học hợp lệ liên kết trong bảng `matakuliah`. | 1. Gửi POST `/jadwal/tambah` với `kelas_id` đã có môn học.<br>2. Giờ: `07:00` - `11:30`, Thứ: `Thứ Hai`. | Lịch học lưu thành công với đúng `matakuliah_id` sẵn có, không tạo thêm bản ghi môn học dư thừa. | Có |
| **TC-SCH-003** | CHK-SCH-003 | **P1 (High)** | Mốc bắt đầu tính buổi học tùy chỉnh (`buoi_bat_dau: 5`). | 1. Gửi form `/jadwal/tambah` với `buoi_bat_dau: 5`.<br>2. Kiểm tra bản ghi trong bảng `jadwal`. | Trường `buoi_bat_dau` trong CSDL được ghi nhận chính xác là `5` (thay vì giá trị mặc định 1). | Có |
| **TC-SCH-004** | CHK-SCH-004 | **P2 (Medium)** | Để trống ô `batas_terlambat` (Hạn đi muộn). | 1. Nhập giờ bắt đầu: `08:00`, để trống hạn đi muộn.<br>2. Gửi form. | Hệ thống tự động tính toán và lưu `batas_terlambat` là `08:15:00` (+15 phút theo cấu hình). | Có |
| **TC-SCH-005** | CHK-SCH-005 | **P0 (Blocker)** | Giờ kết thúc sớm hơn hoặc bằng giờ bắt đầu (`jam_mulai: 10:00`, `jam_selesai: 08:00`). | 1. Nhập Giờ bắt đầu: `10:00`, Giờ kết thúc: `08:00`.<br>2. Bấm "Lưu lịch học". | Hệ thống chặn submit, giữ nguyên form và hiển thị thông báo lỗi màu đỏ: *"Giờ kết thúc phải sau giờ bắt đầu."* Không ghi vào CSDL. | Có |
| **TC-SCH-006** | CHK-SCH-006 | **P1 (High)** | Bỏ trống các trường bắt buộc (không chọn Lớp hoặc Thứ). | 1. Bỏ trống `kelas_id` hoặc `hari`.<br>2. Gửi form POST. | Hiển thị thông báo lỗi: *"Vui lòng nhập đầy đủ thông tin."* | Có |
| **TC-SCH-007** | CHK-SCH-007 | **P0 (Blocker)** | Sửa lịch học tại `/jadwal/edit/<id>` khi form chỉ gửi `kelas_id`. | 1. Mở `/jadwal/edit/<id>`.<br>2. Thay đổi giờ học hoặc thứ.<br>3. Bấm "Cập nhật lịch học". | Cập nhật thành công, không làm đứt gãy khóa ngoại `matakuliah_id`, hiển thị flash message *"Cập nhật lịch học thành công!"*. | Có |

---

## Phân Tích Nguyên Nhân Kỹ Thuật (Bug RCA & Traceability)

- **Nguyên nhân gốc (Root Cause):**
  1. Mô hình CSDL yêu cầu quan hệ phân tầng: `kelas` ➔ `matakuliah` ➔ `jadwal`.
  2. Bảng `jadwal` có ràng buộc toàn vẹn: `FOREIGN KEY (matakuliah_id) REFERENCES matakuliah(id)`.
  3. Khi chuẩn hóa giao diện TMU (1 Lớp = 1 Môn), dropdown chọn môn học được ẩn đi. Tại `app.py`, đoạn code xử lý fallback:
     ```python
     if not mk_id and kelas_id:
         mks = db.get_matakuliah_by_kelas(kelas_id)
         if mks:
             mk_id = mks[0]['id']
         else:
             mk_id = kelas_id  # BUG: kelas_id != matakuliah_id
     ```
     Khi lớp mới tạo chưa có môn học nào trong bảng `matakuliah`, code gán trực tiếp `mk_id = kelas_id`. Do ID này không tồn tại trong bảng `matakuliah`, câu lệnh `INSERT INTO jadwal` vi phạm Foreign Key Constraint `jadwal_ibfk_1` và bị MySQL từ chối.
- **Giải pháp xử lý (Proposed Resolution):**
  Xây dựng cơ chế đảm bảo tự động (Auto-provisioning) `ensure_matakuliah_cho_kelas(kelas_id)`: Nếu lớp học phần chưa có môn học, hệ thống tự động sinh bản ghi môn học tương ứng trong bảng `matakuliah` trước khi lưu lịch học.
