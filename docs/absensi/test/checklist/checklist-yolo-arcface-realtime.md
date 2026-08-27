# Checklist test YOLO + ArcFace realtime

## Scope

Áp dụng cho scan camera nội bộ: YOLOv8-Face 5 landmarks, alignment ArcFace,
gallery embedding, nhận diện realtime, overlay và quyết định điểm danh.

| ID | Hành vi quan sát được | Loại | Ưu tiên | Dữ liệu / trạng thái cần có |
|---|---|---|---:|---|
| RT-HEALTH-01 | `GET /api/face/health` báo ready khi detector, recognizer, gallery và calibration local sẵn sàng | dương | P0 | Model ONNX + gallery hợp lệ |
| RT-HEALTH-02 | Thiếu model, sai output không có 5 landmarks, gallery sai schema hoặc thiếu threshold trả trạng thái rõ; không tự ghi điểm danh | âm | P0 | Từng asset lỗi độc lập |
| RT-DET-01 | Một frame có tối đa 5 mặt trả đủ bbox, `track_id`, `detector_score`, kể cả unknown hoặc lỗi chất lượng | dương | P0 | Frame 1–5 người, có ground-truth số mặt TBD (cần BA cấp) |
| RT-DET-02 | Landmark không hợp lệ, mặt ngoài khung hoặc mặt quá nhỏ không đi vào embedding/điểm danh | âm | P0 | Fixture nhỏ/out-of-frame/landmark-invalid TBD (cần BA cấp) |
| RT-QLT-01 | Mặt tối, quá sáng, mờ và quá nhỏ hiển thị box đỏ cùng `quality_reason` có hướng dẫn | âm/UI | P0 | Fixture chất lượng tương ứng TBD (cần BA cấp) |
| RT-REC-01 | Mặt đã đăng ký, đủ chất lượng và vượt ngưỡng hiển thị nhận diện; chỉ ghi khi đủ số frame xác nhận | dương | P0 | Ảnh/video đã được đồng ý sử dụng |
| RT-REC-02 | Unknown, score dưới ngưỡng, identity conflict hoặc quality lỗi không sinh attendance record | âm | P0 | Người lạ / fixture score mock |
| RT-REC-03 | Threshold chưa hiệu chuẩn hoặc calibration không chấp nhận giữ fail-closed | biên/an toàn | P0 | Bỏ calibration hoặc artifact `accepted=false` |
| RT-LIVE-01 | Liveness chỉ chạy khi track được nhận diện và đạt số frame xác nhận; spoof không được ghi điểm danh | an toàn | P0 | Ảnh/video giả và khuôn mặt thật có đồng ý |
| RT-TRK-01 | Một người di chuyển nhẹ giữ `track_id`, box không nhấp nháy và cache không đổi nhầm danh tính | realtime | P0 | Video một người di chuyển |
| RT-TRK-02 | Người mới thay vị trí cũ làm cache embedding được làm mới; không thừa hưởng ID cũ | âm/an toàn | P0 | Video hai người thay phiên cùng vị trí |
| RT-MULTI-01 | Năm người cùng scan có box/trạng thái riêng; một unknown/spoof không chặn người hợp lệ khác | realtime | P0 | Video 5 người có đồng ý |
| RT-ATT-01 | Mỗi sinh viên chỉ được ghi một lần trong cùng buổi; duplicate trả trạng thái rõ | quyết định | P0 | Lịch học + DB test |
| RT-API-01 | HTTP và WebSocket trả schema per-face: bbox, track_id, detector_score, match_score, display_status, display_label, quality_reason | contract | P0 | Frame hợp lệ / mock engine |
| RT-UI-01 | Overlay map đúng khi mirror/crop; xanh = confirmed, vàng = analysing/calibration, đỏ = unknown/quality/spoof | UI | P0 | Camera browser thực hoặc fixture viewport |
| RT-PERF-01 | Sau warm-up ghi detector latency, embedding latency, end-to-end latency và tốc độ cập nhật box | benchmark | P1 | Laptop target, số mặt 1 và 5; ngưỡng chấp nhận TBD (cần BA cấp) |
| RT-REG-01 | Đăng ký thiếu field, ảnh không đọc được, nhiều mặt/chất lượng không đạt bị từ chối trước khi tạo embedding | âm | P1 | Fixture portrait TBD (cần BA cấp) |
| RT-MAN-01 | Manual correction, export/share kết quả không tự thay đổi recognition result hoặc attendance record ngoài thao tác được xác nhận | regression | P1 | DB/API test fixture |

## Giới hạn đánh giá

- Không khẳng định accuracy/FPS mục tiêu khi chưa có bộ ảnh/video độc lập và ngưỡng chấp nhận được BA phê duyệt.
- Dữ liệu mặt dùng test phải có đồng ý sử dụng; không đưa ảnh, ID sinh viên hay model weight vào Git.
- Test production database, camera và external service phải tách khỏi test tự động bằng fixture/môi trường riêng.
