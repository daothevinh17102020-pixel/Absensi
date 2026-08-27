---
feature: jadwal
title: Quản lý lịch học
primary_device: desktop
screens_count: 5
---

# User Flow — Quản lý lịch học (`/jadwal`)

## 1. Tổng quan
Tài liệu định nghĩa các luồng tương tác người dùng (User Flow) cho tính năng **Quản lý lịch học** thuộc hệ thống điểm danh Absensi, phản ánh đầy đủ các cải tiến UI/UX đã thống nhất.

---

## 2. Danh sách luồng (Flow List)

### Flow 1: Xem & Tìm kiếm lịch học (`danh-sach-jadwal`)
- **Primary Device**: Desktop (1024px) & Mobile (375px)
- **Mô tả**: Quản trị viên xem danh sách lịch học dạng Bảng (Desktop) hoặc Thẻ Card (Mobile), thực hiện tìm kiếm toàn cục có xem trước kết quả.
- **Screens**:
  1. `desktop-table-view`: Màn hình danh sách lịch học dạng Bảng trên Desktop (hiển thị cố định cột Thao tác Sửa/Xóa).
  2. `mobile-card-view`: Màn hình danh sách lịch học dạng Card xếp dọc trên Mobile + Nút tròn nổi FAB `+ Thêm lịch`.
  3. `search-dropdown-active`: Trạng thái gõ từ khóa tìm kiếm toàn cục, hiện dropdown gợi ý kết quả (hỗ trợ phím ESC/Click outside để đóng).

### Flow 2: Thêm & Chỉnh sửa lịch học (`them-sua-jadwal`)
- **Primary Device**: Desktop (1024px)
- **Mô tả**: Quản trị viên tạo mới hoặc chỉnh sửa lịch học bằng Form Grid 2 cột cân đối.
- **Screens**:
  1. `form-grid-layout`: Form tạo/sửa lịch học theo Grid 2 cột (Lớp - Môn, Thứ - Hạn muộn, Giờ bắt đầu - Giờ kết thúc).
  2. `form-auto-delay-preview`: Trạng thái khi chọn Giờ bắt đầu, hệ thống hiển thị gợi ý Hạn đi muộn tức thì.

### Flow 3: Xóa lịch học (`xoa-jadwal`)
- **Primary Device**: Desktop (1024px) / Mobile (375px)
- **Mô tả**: Quản trị viên bấm nút Xóa lịch học, hệ thống mở Modal hộp thoại khóa nền xác nhận.
- **Screens**:
  1. `delete-confirm-modal`: Modal xác nhận xóa có thông báo tên môn + thứ.
