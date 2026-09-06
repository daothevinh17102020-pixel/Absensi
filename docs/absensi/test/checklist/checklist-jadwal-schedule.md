# Checklist Kiểm Thử Nghiệp Vụ & Lịch Học (Jadwal & Academic Schedule)

Tài liệu checklist kiểm thử lịch học tuân thủ tiêu chuẩn `/test-checklist` với cấu trúc grammar chuẩn:
`[P] [Auto] CHK-SCH-NNN → {Ref} · {Nội dung scenario}`

- **P**: Độ ưu tiên `[1]` (Critical/Blocker), `[2]` (High), `[3]` (Medium), `[4]` (Low).
- **Auto**: Khả năng tự động hóa kiểm thử `[Yes]` / `[No]`.
- **Ref**: Mã truy vết tới yêu cầu nghiệp vụ / chức năng học vụ TMU (1 Lớp = 1 Môn học).

---

## 1. Nhóm Khởi Tạo & Thêm Lịch Học Mới (Schedule Creation & TMU 1-to-1 Subject Provisioning)

- [1] [Yes] CHK-SCH-001 → BUG-SCH-001 · Thêm lịch học cho lớp học phần mới tạo (chưa có bản ghi tương ứng trong bảng `matakuliah`) tự động khởi tạo môn học và lưu lịch học thành công, không gây lỗi khóa ngoại `1452 Cannot add or update a child row`.
- [1] [Yes] CHK-SCH-002 → FR-SCH-002 · Thêm lịch học cho lớp học phần đã có sẵn bản ghi môn học hợp lệ liên kết chính xác `matakuliah_id` và điều hướng về `/jadwal`.
- [2] [Yes] CHK-SCH-003 → FR-SCH-003 · Thêm lịch học với mốc buổi học bắt đầu tùy chỉnh (`buoi_bat_dau`, ví dụ: buổi 5) lưu đúng giá trị vào CSDL phục vụ điểm danh giữa kỳ.
- [2] [Yes] CHK-SCH-004 → FR-SCH-004 · Tự động tính toán hạn đi muộn (`batas_terlambat = jam_mulai + 15 phút`) khi người dùng không nhập hoặc để trống.

---

## 2. Nhóm Ràng Buộc Dữ Liệu & Validation Lịch Học (Schedule Validation & Boundary Rules)

- [1] [Yes] CHK-SCH-005 → BR-SCH-001 · Giờ kết thúc trước hoặc bằng giờ bắt đầu (`jam_mulai >= jam_selesai`) bị từ chối với thông báo: *"Giờ kết thúc phải sau giờ bắt đầu."*
- [2] [Yes] CHK-SCH-006 → BR-SCH-002 · Thiếu trường bắt buộc (lớp, thứ, giờ bắt đầu, giờ kết thúc) trả về thông báo lỗi: *"Vui lòng nhập đầy đủ thông tin."*
- [1] [Yes] CHK-SCH-007 → FR-SCH-005 · Cập nhật / Sửa lịch học (`/jadwal/edit/<id>`) chỉ gửi `kelas_id` tự động bảo toàn môn học hợp lệ mà không làm mất liên kết bảng điểm danh.
