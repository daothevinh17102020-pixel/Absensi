# Kế hoạch build: YOLOv8n-Face + ArcFace realtime

## Mục tiêu

Thay luồng scan dashboard bằng detector YOLOv8n-Face có năm landmark, căn
chỉnh mặt, ArcFace embedding, gallery cosine nhiều mẫu, tracker theo bounding
box và phản hồi từng khuôn mặt bằng box màu theo thời gian thực.

## Phạm vi thực hiện

1. **BE/ML** — Nạp hai ONNX model tách biệt; kiểm tra tính sẵn sàng của file,
   parser YOLO `[x, y, w, h, score, 10 landmark]`, NMS, căn chỉnh ArcFace,
   đánh giá chất lượng ảnh, gallery nhiều embedding và tracker IoU có lịch làm
   mới embedding.
2. **API** — Duy trì WebSocket/API hiện có và trả thêm `track_id`,
   `detector_score`, `match_score`, `quality_reason`, `display_status`,
   `display_label` cho từng khuôn mặt; không ghi điểm danh cho mặt lỗi chất
   lượng, unknown hoặc chưa hiệu chuẩn.
3. **FE** — Gửi frame theo backpressure ở nhịp nhanh hơn, hiển thị box xanh,
   vàng, đỏ và chỉ dẫn khắc phục ngay trên từng mặt.
4. **Vận hành** — Không tự tải model. Operator đặt YOLOv8n-Face ONNX có năm
   landmark và ArcFace ONNX đã có quyền sử dụng vào đường dẫn cấu hình, sau đó
   chạy health check và build lại gallery.

## Luồng xử lý

```text
browser camera -> JPEG/WebSocket -> YOLOv8n-Face -> box + landmarks
  -> quality gate -> align -> ArcFace -> cosine gallery -> tracker/cache
  -> trạng thái box -> xác nhận nhiều frame -> ghi điểm danh
```

## Tiêu chí chấp nhận

- Mỗi khuôn mặt detector tìm được luôn có một kết quả/box, kể cả không khớp
  hoặc chất lượng kém.
- Xanh = nhận diện đạt; vàng = đang xác minh/cần hiệu chuẩn; đỏ = không khớp,
  liveness thất bại hoặc có `quality_reason` cụ thể.
- Gallery chứa nhiều embedding hợp lệ cho mỗi sinh viên, không chỉ một vector
  trung bình.
- Không chạy embedding lại cho track vừa được nhận diện trong cửa sổ refresh.
- Thiếu model, output model không có landmark, gallery trống hoặc threshold
  chưa hiệu chuẩn phải báo lỗi/trạng thái rõ ràng thay vì scan im lặng.

## Kiểm thử

- Parser YOLO, alignment, NMS, quality gate, tracker và cosine gallery.
- Multi-face API/WebSocket: năm kết quả có box và trạng thái độc lập.
- Overlay UI: mapping mirror/crop, xanh/vàng/đỏ và quality label.
- Regression: unknown/lỗi chất lượng không được ghi điểm danh.

## Lưu ý license

Chỉ dùng model YOLOv8n-Face và ArcFace mà operator đã được cấp quyền dùng cho
app private. Không commit weight hoặc embedding gallery vào Git.
