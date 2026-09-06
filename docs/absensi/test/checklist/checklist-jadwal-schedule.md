# Checklist Kiểm Thử Toàn Diện Nghiệp Vụ Lịch Học & Khắc Phục Bug (Jadwal & Schedule Suite)

Tài liệu checklist kiểm thử lịch học tuân thủ nghiêm ngặt tiêu chuẩn `/test-checklist` với cấu trúc grammar chuẩn:
`[P] [Auto] CHK-SCH-NNN → {Ref} · {Nội dung scenario}`

- **P**: Độ ưu tiên `[1]` (Critical/Blocker), `[2]` (High), `[3]` (Medium), `[4]` (Low).
- **Auto**: Khả năng tự động hóa kiểm thử `[Yes]` / `[No]`.
- **Ref**: Mã truy vết tới yêu cầu nghiệp vụ / chức năng học vụ TMU (1 Lớp = 1 Môn học).

---

## 1. Nhóm Khởi Tạo & Thêm Mới (Core Flow & TMU Auto-Provisioning)

- [1] [Yes] CHK-SCH-001 → BUG-SCH-001 · Thêm lịch học cho lớp học phần mới tạo (chưa có bản ghi tương ứng trong bảng `matakuliah`) tự động khởi tạo môn học ngầm và lưu lịch học thành công vào CSDL, không gây lỗi khóa ngoại `1452 Cannot add or update a child row`.
- [1] [Yes] CHK-SCH-002 → FR-SCH-002 · Thêm lịch học cho lớp học phần đã có sẵn bản ghi môn học hợp lệ liên kết chính xác `matakuliah_id` sẵn có, không sinh thêm bản ghi môn học rác.
- [2] [Yes] CHK-SCH-003 → FR-SCH-003 · Thêm lịch học với mốc buổi học bắt đầu tùy chỉnh (`buoi_bat_dau`, ví dụ: buổi 5) lưu đúng giá trị vào CSDL phục vụ điểm danh giữa kỳ.
- [2] [Yes] CHK-SCH-004 → FR-SCH-004 · Tự động tính toán hạn đi muộn (`batas_terlambat = jam_mulai + 15 phút`) khi người dùng không nhập hoặc để trống.
- [3] [Yes] CHK-SCH-005 → FR-SCH-005 · Thêm nhiều ca học cho cùng một lớp trong các ngày khác nhau (ví dụ: Thứ Hai và Thứ Năm) lưu trữ độc lập và hiển thị đầy đủ trên danh sách.

---

## 2. Nhóm Cập Nhật & Sửa Đổi (Modification & Data Preservation)

- [1] [Yes] CHK-SCH-010 → FR-SCH-010 · Cập nhật / Sửa lịch học (`/jadwal/edit/<id>`) chỉ gửi `kelas_id` tự động bảo toàn môn học hợp lệ mà không làm mất liên kết bảng điểm danh.
- [2] [Yes] CHK-SCH-011 → FR-SCH-011 · Sửa giờ học hoặc thứ của lịch học cập nhật ngay lập tức sang bảng danh sách và card thông tin ca học trên Dashboard.
- [2] [Yes] CHK-SCH-012 → FR-SCH-012 · Sửa mốc buổi bắt đầu (`buoi_bat_dau`) cập nhật chuẩn xác cách tính số buổi tiếp theo trong `get_buoi_hoc_hien_tai_cua_lop`.
- [3] [Yes] CHK-SCH-013 → E-SCH-001 · Truy cập đường dẫn sửa lịch học với ID không tồn tại (`/jadwal/edit/99999`) điều hướng an toàn về `/jadwal` kèm flash message báo lỗi tiếng Việt.

---

## 3. Nhóm Xóa & Ràng Buộc Toàn Vẹn (Deletion & Cascade Integrity)

- [1] [Yes] CHK-SCH-020 → FR-SCH-020 · Xóa lịch học chưa phát sinh dữ liệu điểm danh (`POST /jadwal/hapus/<id>`) xóa thành công bản ghi khỏi CSDL và chuyển hướng về danh sách với thông báo thành công.
- [2] [Yes] CHK-SCH-021 → BR-SCH-003 · Xóa lịch học đã có sinh viên điểm danh kích hoạt ràng buộc xóa liên đới (CASCADE) hoặc cảnh báo dữ liệu an toàn theo thiết kế DB.
- [2] [Yes] CHK-SCH-022 → BR-SCH-004 · Xóa lớp học (`/kelas/hapus/<id>`) tự động xóa liên đới (CASCADE) môn học và toàn bộ lịch học liên quan.

---

## 4. Nhóm Validation & Phân Tích Giá Trị Biên (Validation & Boundary Value Analysis - BVA)

- [1] [Yes] CHK-SCH-030 → BR-SCH-001 · Giờ kết thúc trước hoặc bằng giờ bắt đầu (`jam_mulai >= jam_selesai`) bị từ chối với thông báo: *"Giờ kết thúc phải sau giờ bắt đầu."*
- [2] [Yes] CHK-SCH-031 → BR-SCH-002 · Thiếu trường bắt buộc (lớp, thứ, giờ bắt đầu, giờ kết thúc) trả về thông báo lỗi: *"Vui lòng nhập đầy đủ thông tin."*
- [3] [Yes] CHK-SCH-032 → BVA-SCH-001 · Giá trị biên buổi học bắt đầu: nhập `buoi_bat_dau = 1` (giá trị tối thiểu hợp lệ) lưu thành công.
- [3] [Yes] CHK-SCH-033 → BVA-SCH-002 · Giá trị biên buổi học bắt đầu: nhập `buoi_bat_dau = 60` (giá trị tối đa hợp lệ) lưu thành công.
- [3] [Yes] CHK-SCH-034 → BVA-SCH-003 · Giá trị không hợp lệ: nhập `buoi_bat_dau <= 0` hoặc chuỗi chữ bị trình duyệt/Backend chặn và chuẩn hóa về tối thiểu 1.
- [2] [Yes] CHK-SCH-035 → BVA-SCH-004 · Khung giờ đặc biệt: Ca học từ `06:00` đến `23:00` (khung giờ xuyên ngày dài nhất) xử lý chính xác định dạng `HH:MM:SS`.

---

## 5. Nhóm Bảo Mật & Phân Quyền (Security & Access Control)

- [1] [Yes] CHK-SCH-040 → SEC-SCH-001 · Truy cập các route quản lý lịch học (`/jadwal`, `/jadwal/tambah`, `/jadwal/edit/<id>`, `/jadwal/hapus/<id>`) khi chưa đăng nhập bị chuyển hướng về `/login`.
- [2] [Yes] CHK-SCH-041 → SEC-SCH-002 · Phiên đăng nhập vai trò Khách (`is_guest: True`) không thể thực hiện thêm/sửa/xóa lịch học (bảo vệ bởi `admin_required`).
- [2] [Yes] CHK-SCH-042 → SEC-SCH-003 · Dữ liệu tên lớp chứa ký tự đặc biệt HTML/Script (`<script>`, `"`, `'`) được render an toàn dưới dạng text, không gây lỗ hổng XSS trên bảng lịch học hoặc modal xác nhận xóa.

---

## 6. Nhóm Điểm Danh Liên Thông & Thời Gian Thực (Attendance & Realtime Schedule Sync)

- [1] [Yes] CHK-SCH-050 → FR-ATT-010 · Lịch học đang diễn ra trong ngày hiện tại (`get_jadwal_aktif`) tự động hiển thị trên Dashboard camera phục vụ quét mặt sinh trắc học.
- [2] [Yes] CHK-SCH-051 → FR-ATT-011 · Popup "Thông tin buổi học" trên Topbar tự động nhận diện ca học gần nhất khớp với danh sách lịch học trong CSDL.
- [2] [Yes] CHK-SCH-052 → FR-ATT-012 · Sinh viên quét mặt đúng giờ học ghi nhận trạng thái `hadir` nếu trước `batas_terlambat`, ghi nhận `terlambat` nếu sau `batas_terlambat`.

---

## 7. Nhóm Giao Diện & Trải Nghiệm Người Dùng (UI/UX & Responsiveness)

- [2] [No] CHK-SCH-060 → UI-SCH-001 · Bảng danh sách lịch học hỗ trợ cuộn ngang (`overflow-x-auto`) mượt mà trên màn hình di động/tablet mà không làm vỡ layout.
- [2] [No] CHK-SCH-061 → UI-SCH-002 · Cột "Thao tác" (Sửa/Xóa) được ghim cố định bên phải (`sticky right-0`) với hiệu ứng đổ bóng mờ chuẩn Dark Mode công nghệ cao.
- [3] [No] CHK-SCH-062 → UI-SCH-003 · Toàn bộ tiêu đề, nhãn input, nút bấm và thông báo tuân thủ font chữ mặc định Open Sans (`font-family: 'Open Sans', sans-serif`).
