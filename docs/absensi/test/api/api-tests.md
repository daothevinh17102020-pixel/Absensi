# Đặc Tả Kiểm Thử API Absensi & Kết Quả Thực Thi

Tài liệu quản lý danh sách test case kiểm thử API tuân thủ tiêu chuẩn `/api-test`. Toàn bộ ca kiểm thử được tự động hóa qua Flask Test Client cô lập, không gọi database production và không làm ảnh hưởng tới dữ liệu thực tế.

<!-- TC:START -->
| Mã TC | Method & Endpoint | Kịch bản / Mục tiêu | Điều kiện tiên quyết | Request Payload | Expected Status & Body | Kết quả | Lần chạy |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **TC-AUTH-001** | `GET /api/search?q=test` | Chưa xác thực gọi API | Không có session | Không | `401 Unauthorized`<br>`{"status": "error"}` | ✅ PASS | 2026-09-05 17:12 |
| **TC-AUTH-002** | `GET /login/guest` | Khách đăng nhập nhanh vào dashboard | Chưa đăng nhập | Không | `302 Redirect` tới `/`<br>Session `is_guest=True` | ✅ PASS | 2026-09-05 17:12 |
| **TC-AUTH-003** | `GET /api/absensi/hari-ini` | Khách truy cập API xem điểm danh | Session Khách (`is_guest=True`) | Không | `200 OK`<br>`{"status": "ok", "data": [...]}` | ✅ PASS | 2026-09-05 17:12 |
| **TC-AUTH-004** | `GET /logout` | Đăng xuất xóa phiên làm việc | Đã có session | Không | `302 Redirect` tới `/login`<br>Session rỗng | ✅ PASS | 2026-09-05 17:12 |
| **TC-ATT-001** | `GET /api/absensi/hari-ini` | Lấy danh sách điểm danh hôm nay | Đã đăng nhập Admin | Không | `200 OK`<br>`{"status": "ok", "data": [...]}` | ✅ PASS | 2026-09-05 17:12 |
| **TC-ATT-002** | `POST /api/absensi/hapus/1` | Xóa lượt điểm danh thành công | Đã đăng nhập Admin, có bản ghi | Không | `200 OK`<br>`{"status": "ok", "pesan": "..."}` | ✅ PASS | 2026-09-05 17:12 |
| **TC-ATT-003** | `POST /api/absensi/hapus/99999` | Xóa lượt điểm danh không tồn tại | Đã đăng nhập Admin | Không | `404 Not Found`<br>`{"status": "error"}` | ✅ PASS | 2026-09-05 17:12 |
| **TC-ATT-004** | `POST /api/absensi/manual` | Điểm danh thủ công payload hợp lệ | Đã đăng nhập Admin, có lịch học | `{"user_id": 1, "jadwal_id": 1, "status": "hadir"}` | `200 OK`<br>`{"status": "ok"}` | ✅ PASS | 2026-09-05 17:12 |
| **TC-ATT-005** | `POST /api/absensi/manual` | Điểm danh thủ công payload sai kiểu | Đã đăng nhập Admin | `{"user_id": "abc", "jadwal_id": 1}` | `400 Bad Request`<br>`{"status": "error"}` | ✅ PASS | 2026-09-05 17:12 |
| **TC-CAM-001** | `GET /api/face/health` | Kiểm tra sức khỏe engine AI thị giác | Đã đăng nhập | Không | `200 OK`<br>`{"ready": true, "gallery_ready": true}` | ✅ PASS | 2026-09-05 17:12 |
| **TC-CAM-002** | `POST /api/camera/toggle` | Đổi trạng thái camera stream | Đã đăng nhập | `{"active": true}` | `200 OK`<br>`{"status": "ok", "active": true}` | ✅ PASS | 2026-09-05 17:12 |
| **TC-CAM-003** | `POST /api/camera/toggle` | Đổi trạng thái camera gửi body sai | Đã đăng nhập | `{"active": "yes"}` | `400 Bad Request`<br>`{"status": "error"}` | ✅ PASS | 2026-09-05 17:12 |
| **TC-SCH-001** | `GET /api/jadwal/hari-ini` | Lấy danh sách lịch học hôm nay | Đã đăng nhập | Không | `200 OK`<br>`{"status": "ok", "data": [...]}` | ✅ PASS | 2026-09-05 17:12 |
| **TC-SCH-002** | `GET /api/mahasiswa/list` | Lấy danh sách sinh viên theo lớp | Đã đăng nhập | `?kelas_id=1` | `200 OK`<br>`{"status": "ok", "data": [...]}` | ✅ PASS | 2026-09-05 17:12 |
| **TC-SCH-003** | `GET /api/search?q=dao` | Tìm kiếm sinh viên theo từ khóa | Đã đăng nhập | Không | `200 OK`<br>`{"status": "ok", "data": {...}}` | ✅ PASS | 2026-09-05 17:12 |
| **TC-SCH-004** | `GET /api/search?q=` | Tìm kiếm từ khóa rỗng | Đã đăng nhập | Không | `200 OK`<br>`{"status": "ok", "data": {...}}` | ✅ PASS | 2026-09-05 17:12 |
| **TC-ENR-001** | `POST /api/foto/upload` | Tải ảnh thiếu thông tin sinh viên | Đã đăng nhập Admin | `{"nama": "", "nim": ""}` | `400 Bad Request`<br>`{"status": "error"}` | ✅ PASS | 2026-09-05 22:58 |
| **TC-TRN-001** | `GET /api/training/status?build_id=invalid` | Tra cứu build_id không tồn tại | Đã đăng nhập Admin | Không | `404 Not Found`<br>`{"status": "error"}` | ✅ PASS | 2026-09-05 22:58 |
| **TC-TRN-002** | `GET /api/training/status?build_id=build-123` | Tra cứu trạng thái huấn luyện hợp lệ | Đã đăng nhập Admin | Không | `200 OK`<br>`{"status": "ok", "data": {...}}` | ✅ PASS | 2026-09-05 22:58 |
| **TC-UTF8-001** | `POST /api/training/start` | Thông điệp JSON UTF-8 & hợp đồng data build_id | Đã đăng nhập Admin, đủ ảnh | `{"nim": "ready-001"}` | `200 OK`<br>`"pesan": "Đã bắt đầu cập nhật gallery khuôn mặt trong nền."`<br>`"data": {"build_id", "state"}` | ✅ PASS | 2026-09-05 23:02 |
| **TC-UTF8-002** | `POST /api/foto/upload` | Thông báo lỗi tiếng Việt UTF-8 chuẩn xác | Đã đăng nhập Admin | `{"nama": "", "nim": ""}` | `400 Bad Request`<br>`"pesan": "Dữ liệu đăng ký khuôn mặt không hợp lệ."` | ✅ PASS | 2026-09-05 23:02 |
| **TC-UTF8-003** | `POST /api/camera/toggle` | Thông báo trạng thái camera tiếng Việt có dấu | Đã đăng nhập | `{"active": true}` | `200 OK`<br>`"pesan": "Máy ảnh đã bật."` | ✅ PASS | 2026-09-05 23:02 |
| **TC-UTF8-004** | `POST /api/absensi/hapus/99999` | Thông báo xóa 404 tiếng Việt có dấu | Đã đăng nhập Admin | Không | `404 Not Found`<br>`"pesan": "Không tìm thấy dữ liệu điểm danh cần xóa."` | ✅ PASS | 2026-09-05 23:02 |
| **TC-UTF8-005** | `GET /api/absensi/hari-ini` | JSON UTF-8 nguyên bản (ensure_ascii=False) | Đã đăng nhập | Không | `200 OK`<br>Raw bytes UTF-8 có dấu (không bị escape `\u0110...`) | ✅ PASS | 2026-09-05 23:03 |
<!-- TC:END -->

---

## Ghi Chú Môi Trường & Nguyên Tắc Bảo Mật
- Không gọi database production và không chứa secrets trong code test.
- Mọi thao tác I/O file ảnh đăng ký được cô lập trong thư mục test tạm thời (`tmp/`).
- Các tính năng ngoài phạm vi (ESP32 phần cứng, Google Form/Drive chưa có contract API) được ghi nhận trạng thái PENDING theo quy chuẩn.
