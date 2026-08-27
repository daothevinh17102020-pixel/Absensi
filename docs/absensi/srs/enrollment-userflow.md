---
feature: enrollment
title: Đăng ký khuôn mặt (Face Enrollment)
primary_device: desktop
screens_count: 2
---

# User Flow — Đăng ký khuôn mặt (`/enrollment`)

## 1. Tổng quan
Tài liệu định nghĩa các luồng tương tác người dùng cho tính năng **Đăng ký khuôn mặt (Face Enrollment)**, tập trung nâng cấp trải nghiệm quét ảnh với giao diện HUD (Heads-Up Display) hiển thị thanh tiến độ và số lượng ảnh ngay trên khung Video camera.

---

## 2. Danh sách luồng (Flow List)

### Flow 1: Đăng ký khuôn mặt giao diện HUD (`scan-face-hud`)
- **Primary Device**: Desktop (1024px) & Mobile (375px)
- **Mô tả**: Sinh viên/Quản trị viên thực hiện chụp 24 ảnh khuôn mặt. Thanh tiến độ màu cam và thông số `6/24` được đưa trực tiếp lên đè trên khung Video Camera (HUD overlay) giúp người dùng giữ tầm nhìn tập trung vào ống kính.
- **Screens**:
  1. `desktop-hud-overlay`: Giao diện chụp khuôn mặt trên Desktop với thanh tiến độ màu cam đè trên khung video (Overlay góc trên/dưới khung hình camera).
  2. `mobile-hud-overlay`: Giao diện chụp khuôn mặt di động tối ưu khung hình dọc kèm thanh tiến độ cam trên màn hình camera.
  3. `scan-completed-modal`: Trạng thái khi hoàn tất 24/24 ảnh, hiển thị badge thành công và nút chuyển sang bước lưu hồ sơ.
