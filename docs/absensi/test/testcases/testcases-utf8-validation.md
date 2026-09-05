# Bộ Ca Kiểm Thử Xác Thực Font UTF-8 & Nội Dung Thông Báo (Popup / Alert / Toast)

> **Phạm vi kiểm thử:** Toàn bộ popup modal, toast notification, flash message, và API messages trên toàn hệ thống Absensi sau khi chuẩn hóa Unicode UTF-8 (NFC).  
> **Phương pháp:** Bám sát checklist kiểm thử 1:1, kiểm tra hiển thị tiếng Việt có dấu, không lỗi font mojibake, câu từ chuẩn mực chính tả IT-BA.

---

## Danh Sách Ca Kiểm Thử Chi Tiết

| Mã TC | Màn hình / Thành phần | Kịch bản kiểm thử | Dữ liệu đầu vào | Thao tác thực hiện | Kết quả mong đợi | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **TC-UI-UTF8-001** | Modal Đăng nhập (`/login`) | Thông báo lỗi khi để trống tài khoản hoặc mật khẩu | Tên đăng nhập: rỗng, Mật khẩu: rỗng | Nhấn nút "Đăng nhập" | Hiển thị thông báo màu đỏ: *"Vui lòng nhập tên đăng nhập và mật khẩu."* Không dính lỗi mojibake `Vui lÃ²ng...` | ✅ PASS |
| **TC-UI-UTF8-002** | Modal Đăng nhập (`/login`) | Thông báo lỗi khi nhập sai mật khẩu | Username: `admin`, Password: `sai` | Nhấn nút "Đăng nhập" | Hiển thị thông báo: *"Tên đăng nhập hoặc mật khẩu không đúng."* Chuẩn UTF-8 sắc nét | ✅ PASS |
| **TC-UI-UTF8-003** | Toast Dashboard (`/`) | Khách tham gia chế độ xem điểm danh | Click nút "Tham gia với vai trò Khách" | Điều hướng vào Dashboard | Xuất hiện Toast info: *"Đã tham gia với vai trò Khách (Chế độ Điểm danh)."* | ✅ PASS |
| **TC-UI-UTF8-004** | Modal Thêm Lớp (`/kelas/tambah`) | Thông báo thành công khi thêm lớp mới | Tên lớp: `K58CC1`, Khóa: `2022-2026` | Nhấn "Lưu lớp" | Flash message màu xanh: *"Thêm lớp thành công!"* Chuẩn UTF-8, tự động biến mất sau 4s | ✅ PASS |
| **TC-UI-UTF8-005** | Modal Xóa Lớp (`/kelas/index`) | Cảnh báo xóa lớp có ràng buộc dữ liệu | Lớp có sinh viên liên kết | Nhấn "Xóa" trong modal xác nhận | Flash message màu đỏ: *"Không thể xóa lớp. Có thể lớp vẫn còn sinh viên liên quan."* | ✅ PASS |
| **TC-UI-UTF8-006** | Modal Thêm Môn (`/matakuliah/form`) | Thông báo thành công khi thêm môn học | Tên môn: `Học máy`, Mã môn: `ML01` | Nhấn "Lưu môn học" | Flash message: *"Thêm môn học thành công!"* | ✅ PASS |
| **TC-UI-UTF8-007** | Modal Đăng Ký SV (`/mahasiswa/register`) | Thông báo xác nhận đăng ký thông tin thành công | Họ tên: `Nguyễn Văn A`, Mã SV: `22D190001` | Nhấn "Chỉ lưu thông tin" | Flash message: *"Đăng ký sinh viên Nguyễn Văn A thành công! Hãy tiếp tục chụp ảnh sinh trắc học."* | ✅ PASS |
| **TC-UI-UTF8-008** | Camera Modal (`/mahasiswa/register`) | Hướng dẫn 24 góc quét camera real-time | Camera kích hoạt | Nhấn "Bắt đầu chụp ảnh" | Label hướng dẫn: *"Ảnh đạt yêu cầu — giữ yên để máy chụp (1/3)"*, *"Đã chụp 24/24 ảnh."* Không lỗi font | ✅ PASS |
| **TC-UI-UTF8-009** | Popup Hoàn tất Đăng ký (`/mahasiswa/register`) | Màn hình hoàn tất 24 góc quét | Quét đủ 24 ảnh | Hoàn tất background build gallery | Modal hiển thị: *"Gallery đã sẵn sàng. Hoàn tất đăng ký!"*, *"Đăng ký sinh viên thành công!"* | ✅ PASS |
| **TC-UI-UTF8-010** | Overlay Camera Dashboard (`/`) | Cảnh báo phát hiện giả mạo camera | Ảnh trên điện thoại hoặc ảnh in | Đưa trước camera | Overlay camera hiện: *"⚠️ Phát hiện giả mạo! Vui lòng sử dụng khuôn mặt thật."* Màu đỏ cảnh báo | ✅ PASS |
| **TC-UI-UTF8-011** | Toast Camera Dashboard (`/`) | Ghi nhận điểm danh thành công | Sinh viên hợp lệ có trong gallery | Đưa mặt vào camera | Toast success: *"Đã ghi nhận điểm danh: [Tên SV] — Có mặt"* và cập nhật bảng điểm danh realtime | ✅ PASS |
| **TC-UI-UTF8-012** | Modal Xuất Báo Cáo (`/laporan`) | Tiêu đề và nội dung xuất file Excel | Chọn kỳ học và bấm xuất | Tải file `.xlsx` | Tiêu đề trang tính: *"Tổng hợp điểm danh"*, Header: `Họ và tên`, `Mã sinh viên`, `Lớp`, `Thứ`, `Ngày`, `Thời gian điểm danh` | ✅ PASS |

---

## Đánh Giá Tổng Hợp Nghiệm Thu
- 100% các chuỗi mojibake đã được giải quyết triệt để tại tầng Backend (`app.py`), không còn phụ thuộc vào các đoạn script vá tạm thời tại DOM Frontend.
- Các API JSON trả về tiếng Việt UTF-8 nguyên bản (`ensure_ascii=False`), giúp các thông báo Toast và Overlay động hiển thị sắc nét, chuyên nghiệp.
- Hoàn toàn bảo toàn 100% logic ML và hợp đồng dữ liệu của 2 tính năng key.
