# Test case regression Absensi

| ID | Checklist | Pri | Tiền điều kiện / dữ liệu | Bước chính | Kết quả mong đợi | Tự động hóa |
|---|---|---:|---|---|---|---|
| TC-AUTH-01 | CL-AUTH-01 | P0 | session trống | GET trang HTML và GET/POST API | HTML 302; API JSON 401, schema ổn định | Có |
| TC-API-01 | CL-API-01 | P0 | session mock | Gửi null, array, string, boolean, sai content-type | JSON 400; DB không được gọi | Có |
| TC-API-02 | CL-API-02 | P0 | DB helper mock raise | Gọi API danh sách/tìm kiếm | 5xx; không lộ `str(e)` | Có |
| TC-UP-01 | CL-ENR-01/02 | P0 | ảnh giả cục bộ | Gửi thiếu field, sai type, base64 lỗi, bytes không phải ảnh | 400; không tạo user/file | Có |
| TC-UP-02 | CL-ENR-04 | P0 | thư mục tạm có `0.jpg` | Upload lại index 0 | 409/400; hash file cũ không đổi | Có |
| TC-UP-03 | CL-ENR-03 | P1 | TBD (cần BA cấp ảnh 0/1/nhiều mặt) | Upload từng fixture | Kết quả theo rule đã đặc tả, không suy diễn accuracy | Một phần |
| TC-REC-01 | CL-REC-01/02 | P0 | prediction/DB mock | Chạy unknown, low-confidence, duplicate, conflict, success | Chỉ success đủ điều kiện ghi DB; token máy giữ nguyên | Có |
| TC-REC-02 | CL-REC-03 | P0 | multi-face result có nested spoof score | Render kết quả | Hiện đúng score; cảnh báo không bị che | Có |
| TC-MAN-01 | CL-MAN-01 | P0 | user/lịch mock | Gửi ID chữ, 0, âm, sai lớp/ngày/status | JSON 400 phù hợp; không ghi DB | Có |
| TC-MAN-02 | CL-MAN-02 | P0 | cùng số bản ghi, status đổi | Poll lại `/api/absensi/hari-ini` | DOM cập nhật nội dung mới | Có |
| TC-EXP-01 | CL-EXP-01 | P0 | bộ lọc lớp/môn/từ/đến | Click CSV/XLSX và kiểm tra args DB | URL hợp lệ; đủ filter; header tiếng Việt | Có |
| TC-XSS-01 | CL-UI-01 | P0 | chuỗi `<img src=x onerror=...>` | Render overlay, row và toast | Chuỗi là text; không tạo node img/script | Có |
| TC-I18N-01 | CL-I18N-01 | P0 | năm status + bảy ngày | Submit/render/export | value/payload cũ; label tiếng Việt | Có |
| TC-CAM-01 | CL-CAM-01 | P0 | session mock | Gửi true/false và `"false"`, 0, null | boolean hợp lệ; sai type trả 400 | Có |
| TC-CAM-02 | CL-CAM-02 | P1 | hai Socket.IO client mock | Toggle độc lập, disconnect | tracker/state không rò giữa client | Có |
| TC-CLS-01 | CL-CLS-01 | P1 | TBD (cần BA cấp ảnh lớp) | Gửi lỗi upload/no-face | Trạng thái lỗi rõ, không ghi điểm danh | Một phần |
| TC-ATT-01 | CL-ATT-01 | P1 | lịch kết thúc + user chưa có bản ghi, toàn bộ DB mock | Chạy một vòng auto-alpha | Chỉ user đủ điều kiện nhận token `alpha`; không tạo trùng | Có |
| TC-TRN-01 | CL-TRN-01 | P1 | training worker và lock mock | Gọi start hai lần, kết thúc worker rồi gọi lại | Lần chồng lấn 409; lock được giải phóng | Có |
| TC-MODEL-01 | CL-REC-01 | P1 | `FaceEngineError` mock | POST frame hợp lệ | JSON 503, `tipe=model_unavailable`, không ghi DB | Có |
| TC-EXT-01 | CL-EXT-01 | P0 | DB/filesystem/model mock và thư mục tạm | Chạy toàn bộ API/export tests | Không kết nối production, không đọc secret, không ghi ngoài temp | Có |
