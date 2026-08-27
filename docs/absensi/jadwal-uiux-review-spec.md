# ĐẶC TẢ YÊU CẦU NÂNG CẤP UI/UX TRANG QUẢN LÝ LỊCH HỌC (/jadwal)

> **Mã tài liệu**: UIUX-JADWAL-SPEC-01  
> **Trạng thái**: Chờ lập trình viên triển khai (Pending Code)  
> **Ứng dụng URL**: http://127.0.0.1:5000/jadwal  
> **Đường dẫn file tuyệt đối**: `e:\TMU UNIVERSITY\MACHINE LEARNING\SOURCE 1_ƯU TIÊN\Absensi\docs\absensi\jadwal-uiux-review-spec.md`

---

## 1. MỤC TIÊU & PHẠM VI
Tài liệu này tổng hợp chi tiết các vấn đề trải nghiệm người dùng (UX) và giao diện (UI) hiện tại của trang **Quản lý lịch học (`/jadwal`)**, đồng thời đưa ra yêu cầu thiết kế chi tiết để lập trình viên tiến hành nâng cấp code ở bước tiếp theo mà không làm gián đoạn luồng nghiệp vụ hiện tại.

---

## 2. DANH SÁCH CHI TIẾT CÁC HẠNG MỤC CẦN CHỈNH SỬA

### Hạng mục 1: Tương thích thiết bị di động (Responsive Design & Mobile UX)
- **Vấn đề hiện tại**:
  1. Thanh Header trên mobile bị xô lệch: Ô tìm kiếm và các biểu tượng (Thông báo, Cài đặt, User) bị dồn dập sát lề phải; nút `+ Thêm lịch học` bị đẩy tràn ra khỏi viewport màn hình.
  2. Bảng dữ liệu (`<table>`) bị cắt cụt cạnh phải: Cột `Hạn đi muộn` và cột `Thao tác` bị ẩn mất trên di động mà không có thanh cuộn ngang.
  3. Thẻ Badge bị vỡ chữ: Thẻ `Thứ Năm` bị tách thành 2 dòng (`Thứ` / `Năm`), tên lớp `ML-01` bị đứt gãy (`ML-` / `01`).
- **Yêu cầu chỉnh sửa**:
  1. **Bọc bảng dữ liệu**: Bọc bảng trong thẻ `<div class="overflow-x-auto">` để cho phép cuộn ngang mượt mà trên màn hình hẹp (`< 768px`).
  2. **Chuyển Card View trên Mobile**: Với màn hình di động nhỏ (`< 640px`), khuyến nghị ẩn hẳn `<table>` và render danh sách dưới dạng danh sách Thẻ (Card View) xếp dọc.
  3. **Cố định phông chữ Badge**: Thêm `white-space: nowrap` cho toàn bộ thẻ Badge (Thứ) và Mã lớp để giữ nguyên cấu trúc văn bản.
  4. **Nút Thêm mới trên Mobile**: Trên thiết bị di động, ẩn nút `+ Thêm lịch học` ở Header và chuyển thành Nút tròn nổi **FAB (Floating Action Button)** cố định ở góc dưới bên phải màn hình (`bottom: 24px`, `right: 24px`).

---

### Hạng mục 2: Tương tác & Thao tác trên Bảng (Table Interactions & Actions)
- **Vấn đề hiện tại**:
  1. Nút `Xóa` bị cài đặt `opacity-0` (chỉ hiển thị khi hover chuột). Trên thiết bị cảm ứng di động, không có sự kiện hover làm người dùng không thể thực hiện hành động xóa.
  2. Đang thiếu hoàn toàn nút/chức năng **Chỉnh sửa lịch học (Edit Schedule)**.
- **Yêu cầu chỉnh sửa**:
  1. **Hiển thị cột Thao tác rõ ràng**: Bỏ thuộc tính ẩn hover `opacity-0`. Hiển thị cột `THAO TÁC` cố định ở bên phải bảng với 2 nút icon:
     - Icon ✏️ (Edit): Chỉnh sửa thông tin lịch học.
     - Icon 🗑️ (Delete): Xóa lịch học (Màu đỏ mờ `text-red-400 hover:text-red-300`).
  2. **Bổ sung Modal/Trang Chỉnh sửa**: Tạo luồng sửa lịch học cho phép cập nhật Giờ bắt đầu, Giờ kết thúc và Thứ mà không cần phải xóa đi tạo lại.
  3. **Giữ nguyên Modal Cảnh báo Xóa**: Duy trì modal xác nhận xóa có focus trap và thông báo chi tiết (*"Bạn có chắc chắn muốn xóa lịch học Machine Learning - Thứ Năm?"*).

---

### Hạng mục 3: Bố cục Form Thêm/Sửa Lịch Học (`/jadwal/tambah`)
- **Vấn đề hiện tại**:
  1. Form nhập liệu kéo dài tràn 100% chiều ngang màn hình Desktop, làm các ô select box bị dãn dài quá mức, khoảng trắng thừa nhiều.
- **Yêu cầu chỉnh sửa**:
  1. **Tái cấu trúc Grid 2 cột**: Đổi layout Form từ 1 cột đứng thành **Grid 2 cột cân đối** (`grid grid-cols-1 md:grid-cols-2 gap-6`) trên Desktop:
     - **Hàng 1**: [Lớp học] | [Môn học (Phụ thuộc vào lớp)]
     - **Hàng 2**: [Thứ trong tuần] | [Hạn đi muộn (Tự động tính = Giờ bắt đầu + 15 phút)]
     - **Hàng 3**: [Giờ bắt đầu (HH:mm)] | [Giờ kết thúc (HH:mm)]
  2. **Xem trước Hạn đi muộn tức thì**: Khi người dùng chọn Giờ bắt đầu, hệ thống cần nhảy dữ liệu gợi ý Hạn đi muộn ngay lập tức trên UI để người dùng kiểm tra trước khi nhấn Submit.

---

### Hạng mục 4: Tương tác Thanh Tìm Kiếm Toàn Cục (Global Search Component)
- **Vấn đề hiện tại**:
  1. Dropdown gợi ý kết quả tìm kiếm không tự ẩn khi bấm chuột ra ngoài khung tìm kiếm hoặc khi nhấn phím `Escape`.
- **Yêu cầu chỉnh sửa**:
  1. Bổ sung sự kiện `click outside` (`document.addEventListener('click')`) hoặc `onBlur`.
  2. Bắt phím `Escape` (`Keydown: Escape`) để ẩn ngay lập tức khung Dropdown kết quả tìm kiếm.

---

## 3. ĐỐI CHIẾU FILE NGUỒN CẦN SỬA CODE (SOURCE CODE MAPPING)
Khi tiến hành code lại sau này, lập trình viên sẽ trực tiếp cập nhật các file HTML/Jinja2 sau:
- **Trang danh sách lịch học (`/jadwal`)**: [index.html](file:///e:/TMU%20UNIVERSITY/MACHINE%20LEARNING/SOURCE%201_%C6%AFU%20TI%C3%8AN/Absensi/templates/jadwal/index.html)
- **Form Thêm/Sửa lịch học (`/jadwal/tambah`)**: [form.html](file:///e:/TMU%20UNIVERSITY/MACHINE%20LEARNING/SOURCE%201_%C6%AFU%20TI%C3%8AN/Absensi/templates/jadwal/form.html)
- **Template tham chiếu UI tĩnh**: [code.html](file:///e:/TMU%20UNIVERSITY/MACHINE%20LEARNING/SOURCE%201_%C6%AFU%20TI%C3%8AN/Absensi/templates/stitch/manajemen_jadwal_sistem_absensi/code.html)

---

## 4. TỔNG HỢP KẾT QUẢ REVIEW TỪ AGY CLI (DRAFT REVIEWER)

| STT | Phát hiện / Khuyến nghị từ Agy CLI | Bằng chứng (Evidence) | Phân loại từ Main Agent | Ghi chú & Hành động |
|---|---|---|---|---|
| 1 | Bổ sung đường dẫn file template thực tế (`index.html`, `form.html`) | Đã tìm thấy file trong `templates/jadwal/` | **Accept** | Đã map trực tiếp đường dẫn file Jinja2 vào Mục 3 của đặc tả này. |
| 2 | Chú ý kiểm tra xem các class Tailwind trên mobile có bị xung đột giữa layout `stitch` và `jadwal` không | File `templates/stitch/.../code.html` có một số class CSS tùy biến | **Accept** | Khi sửa code sau này, ưu tiên dùng chuẩn Tailwind CSS thuần, loại bỏ class cứng pixel. |
| 3 | Tách riêng tài liệu cho từng màn hình khác | Đề xuất phân rã tài liệu | **Defer** | Chưa cần thiết ở thời điểm hiện tại. Tập trung 1 file duy nhất cho trang `/jadwal` đúng theo Single Output File Rule. |

---

## 5. LINK & THÔNG TIN TRA CỨU
- **Link App chạy thực tế**: http://127.0.0.1:5000/jadwal
- **Đường dẫn file đặc tả này (Tuyệt đối)**: `e:\TMU UNIVERSITY\MACHINE LEARNING\SOURCE 1_ƯU TIÊN\Absensi\docs\absensi\jadwal-uiux-review-spec.md`
