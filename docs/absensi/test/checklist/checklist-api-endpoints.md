# Checklist Kiểm Thử API Endpoints — Hệ Thống Điểm Danh Sinh Trắc Học Absensi

Tài liệu checklist kiểm thử API tuân thủ tiêu chuẩn `/test-checklist` với cấu trúc grammar chuẩn:
`[P] [Auto] CHK-API-NNN → {Ref} · {Nội dung scenario}`

- **P**: Độ ưu tiên `[1]` (Critical/Blocker), `[2]` (High), `[3]` (Medium), `[4]` (Low).
- **Auto**: Khả năng tự động hóa kiểm thử `[Yes]` / `[No]`.
- **Ref**: Mã truy vết tới yêu cầu nghiệp vụ / chức năng.

---

## 1. Nhóm Xác Thực & Quyền Truy Cập (Auth & Session Boundary)

- [1] [Yes] CHK-API-001 → FR-AUTH-001 · Gửi request tới bất kỳ endpoint `/api/*` khi chưa đăng nhập trả về HTTP 401 và JSON error thống nhất.
- [1] [Yes] CHK-API-002 → FR-AUTH-002 · Đăng nhập vai trò Khách (`/login/guest`) cấp session `is_guest: True` và cho phép truy cập các API đọc dữ liệu Dashboard.
- [2] [Yes] CHK-API-003 → FR-AUTH-003 · Truy cập API quản trị yêu cầu quyền Admin (`admin_required`) từ session Khách bị từ chối với HTTP 401/403.
- [2] [Yes] CHK-API-004 → FR-AUTH-004 · Đăng xuất (`/logout`) xóa toàn bộ session `admin_id` và `is_guest`, thu hồi quyền truy cập API ngay lập tức.

---

## 2. Nhóm Điểm Danh Thời Gian Thực & Camera AI (Realtime Attendance & Vision)

- [1] [Yes] CHK-API-010 → FR-ATT-001 · `GET /api/absensi/hari-ini`: Trả về danh sách sinh viên đã điểm danh trong ngày với HTTP 200 và cấu trúc mảng JSON chuẩn.
- [1] [Yes] CHK-API-011 → FR-ATT-002 · `POST /api/absensi/hapus/<absensi_id>`: Xóa thành công bản ghi điểm danh hôm nay với HTTP 200, cho phép sinh viên quét mặt điểm danh lại.
- [2] [Yes] CHK-API-012 → E-ATT-001 · `POST /api/absensi/hapus/<absensi_id>`: Xóa với ID không tồn tại hoặc đã bị xóa trả về HTTP 404 và thông báo tiếng Việt an toàn.
- [1] [Yes] CHK-API-013 → FR-ATT-003 · `POST /api/absensi/manual`: Điểm danh thủ công với payload hợp lệ (user_id, jadwal_id, status) ghi nhận bản ghi và trả về HTTP 200.
- [2] [Yes] CHK-API-014 → E-ATT-002 · `POST /api/absensi/manual`: Payload thiếu trường, sai kiểu dữ liệu (chuỗi thay vì số) hoặc trạng thái không hợp lệ bị từ chối với HTTP 400.
- [1] [Yes] CHK-API-015 → FR-CAM-001 · `GET /api/face/health`: Trả về trạng thái hoạt động của mô hình AI nhận diện (YOLOv8 + ArcFace) và trạng thái sẵn sàng của camera.
- [2] [Yes] CHK-API-016 → FR-CAM-002 · `POST /api/camera/toggle`: Bật/Tắt trạng thái hoạt động của camera stream từ client với HTTP 200.
- [2] [Yes] CHK-API-017 → FR-CAM-003 · `POST /api/absensi/proses`: Xử lý khung hình nhận diện fallback qua HTTP trả về kết quả bounding box và spoofing score.

---

## 3. Nhóm Học Vụ, Lớp & Lịch Học (Academic & Schedule)

- [1] [Yes] CHK-API-020 → FR-SCH-001 · `GET /api/jadwal/hari-ini`: Trả về danh sách các ca học đang diễn ra trong ngày hiện tại khớp với lịch nhà trường.
- [2] [Yes] CHK-API-021 → FR-MHS-001 · `GET /api/mahasiswa/list`: Trả về danh sách sinh viên theo lớp lọc hoặc toàn trường dưới dạng JSON.
- [2] [Yes] CHK-API-022 → FR-SRCH-001 · `GET /api/search?q=<từ_khóa>`: Tìm kiếm sinh viên theo tên hoặc mã sinh viên (NIM) trả về kết quả gợi ý tức thì.
- [3] [Yes] CHK-API-023 → E-SRCH-001 · `GET /api/search`: Gửi từ khóa rỗng trả về mảng kết quả rỗng với HTTP 200 mà không gây crash server.

---

## 4. Nhóm Đăng Ký Sinh Viên 24 Góc Chụp & Huấn Luyện ArcFace (Enrollment & Training)

- [1] [Yes] CHK-API-030 → FR-ENR-001 · `POST /api/foto/upload`: Tải lên ảnh khuôn mặt kèm góc chụp (index 0..23) kiểm tra tính hợp lệ base64 và lưu tạm thư mục dataset.
- [2] [Yes] CHK-API-031 → E-ENR-001 · `POST /api/foto/upload`: Gửi ảnh hỏng, định dạng không phải ảnh hoặc thiếu thông tin sinh viên trả về HTTP 400.
- [1] [Yes] CHK-API-032 → FR-TRN-001 · `POST /api/training/start`: Kích hoạt tiến trình huấn luyện cập nhật Gallery vector đặc trưng ArcFace trong background thread.
- [2] [Yes] CHK-API-033 → E-TRN-001 · `POST /api/training/start`: Kích hoạt khi tiến trình huấn luyện khác đang chạy trả về HTTP 409 (Conflict).
- [1] [Yes] CHK-API-034 → FR-TRN-002 · `GET /api/training/status`: Truy vấn tiến độ huấn luyện trả về trạng thái (`idle`, `training`, `success`, `error`) và số lượng template hoàn tất.
