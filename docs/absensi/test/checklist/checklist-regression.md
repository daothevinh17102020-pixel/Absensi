# Checklist regression và API Absensi

| ID | Hành vi quan sát được | Loại | Ưu tiên |
|---|---|---|---|
| CL-AUTH-01 | Trang HTML chưa đăng nhập chuyển tới `/login`; API chưa đăng nhập trả JSON 401 | âm | P0 |
| CL-API-01 | API từ chối body không phải JSON object và sai kiểu field bằng JSON 400 | biên/âm | P0 |
| CL-API-02 | API lỗi nội bộ trả 5xx, schema ổn định và không lộ exception | âm | P0 |
| CL-ENR-01 | Thiếu tên, mã sinh viên, lớp hoặc ảnh bị từ chối trước khi tạo sinh viên | âm | P0 |
| CL-ENR-02 | Ảnh base64 lỗi/không đọc được bị từ chối và không ghi file | âm | P0 |
| CL-ENR-03 | Ảnh chân dung không có mặt, nhiều mặt hoặc chất lượng không đạt | review | P1 |
| CL-ENR-04 | Upload trùng index không ghi đè ảnh đã có | biên | P0 |
| CL-CLS-01 | Upload ảnh lớp thất bại hoặc không có khuôn mặt trả trạng thái rõ ràng | âm | P1 |
| CL-REC-01 | Unknown, low-confidence, duplicate candidate và identity conflict không ghi điểm danh sai | quyết định | P0 |
| CL-REC-02 | Khuôn mặt hợp lệ tạo bản ghi Có mặt/Đi muộn đúng token máy | dương | P0 |
| CL-REC-03 | Spoofing hiển thị đúng điểm và không bị kết quả thành công khác che khuất | âm | P0 |
| CL-MAN-01 | Điểm danh thủ công chỉ nhận ID dương, lịch hôm nay, đúng lớp và năm trạng thái hợp lệ | biên | P0 |
| CL-MAN-02 | Sửa trạng thái giữ nguyên số bản ghi nhưng dashboard vẫn cập nhật | regression | P0 |
| CL-ATT-01 | Sinh viên không có bản ghi sau lịch đủ điều kiện được xử lý vắng theo rule hiện có | quyết định | P1 |
| CL-EXP-01 | CSV/XLSX nhận đúng toàn bộ bộ lọc và dùng tiêu đề tiếng Việt | dương | P0 |
| CL-UI-01 | Dữ liệu người dùng được hiển thị như text, không thực thi HTML/script | bảo mật UI | P0 |
| CL-I18N-01 | Nhãn UI là tiếng Việt; token `hadir/terlambat/izin/sakit/alpha` và `Senin…Minggu` không đổi trong payload/lưu trữ | contract | P0 |
| CL-CAM-01 | Camera toggle chỉ nhận boolean và phản hồi đúng trạng thái | biên | P0 |
| CL-CAM-02 | Hai client không làm sai trạng thái/tracker của nhau | đồng thời | P1 |
| CL-TRN-01 | Training lock từ chối lần chạy chồng lấn và giải phóng sau khi worker kết thúc | đồng thời | P1 |
| CL-EXT-01 | Export/chia sẻ kết quả không gọi dữ liệu production trong test | an toàn | P0 |

Các mục cần fixture thật nhưng hiện chưa có (`CL-ENR-03`, một phần `CL-CLS-01`, đo ML accuracy) được ghi `TBD (cần BA cấp)` và không được suy diễn kết quả.
