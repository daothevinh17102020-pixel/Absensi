# Review implementation: YOLO + ArcFace realtime

## Nguồn review

- Agy CLI (draft reviewer, không sửa file): 7 finding.
- Codex CLI read-only (draft reviewer, không sửa file): 12 finding.
- Main review đối chiếu trực tiếp source và chạy regression trong `.venv`.

## Quyết định finding

| Nhóm finding | Quyết định | Lý do / xử lý |
|---|---|---|
| Tách InsightFace wrapper thành ONNX detector + recognizer | Accept | `face/yolo_arcface.py` dùng hai `onnxruntime.InferenceSession` độc lập. |
| 5 landmarks và alignment ArcFace | Accept | Contract detector yêu cầu 5 điểm; `estimateAffinePartial2D` căn về template 112x112. |
| Gallery nhiều embedding/mỗi người | Accept | Gallery schema 2 lưu từng embedding hợp lệ; score của user là max cosine trong templates của user đó. |
| Tracking trước recognition và cache embedding | Accept, điều chỉnh | Đã dùng tracker IoU detector-first cho tối đa 5 mặt và cache theo `track_id`. Đây chưa phải ByteTrack đầy đủ (không Kalman/Hungarian/low-score association); adapter được tách để thay bằng ByteTrack sau mà không đổi API. |
| Quality gate và trạng thái đỏ | Accept | Có too-small, sáng/tối, blur, landmark/out-of-frame; không embedding hay điểm danh khi lỗi. |
| Frame 1.2s + khoá 3s | Accept | Client còn một frame in-flight nhưng gửi lại sau 250ms và bỏ khoá 3 giây toàn cục. |
| Liveness chạy mọi frame | Accept | Chỉ chạy sau khi track recognized đủ số frame xác nhận. |
| Health/model provenance | Accept | `/api/face/health`, không auto-download; có manifest mẫu. |
| Chuyển payload base64 sang binary Socket.IO | Defer | Có lợi nhưng cần benchmark transport thực tế, chưa thay đổi protocol đang dùng để tránh phá client/API hiện hữu. |
| Xóa legacy Haar/LBPH | Defer | Các entry point cũ không nằm trên luồng dashboard mới; không xóa khi worktree đang có thay đổi chưa commit. |
| Đặt threshold cosine cố định | Reject | Không có tập hiệu chuẩn với đúng ONNX được cấp quyền; hệ thống fail-closed khi `FACE_MATCH_THRESHOLD` chưa đặt. |

## Kết quả xác minh

```text
.venv\Scripts\python.exe -m unittest discover -s tests
Ran 45 tests in 0.079s
OK (skipped=3 DB integration tests)
```

Health check hiện fail đúng chủ đích cho đến khi operator đặt model ONNX hợp lệ:

```text
Khong tim thay YOLOv8n-Face ONNX tai models/yolo/yolov8n-face-5kps.onnx
```
