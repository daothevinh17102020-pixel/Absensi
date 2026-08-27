# Kế hoạch build tạm — Scanner tối đa 10 khuôn mặt

## Mục tiêu đã chốt

- Một frame chỉ xử lý tối đa 10 khuôn mặt có `detector_score` cao nhất sau YOLO + NMS.
- Mỗi khuôn mặt xác minh độc lập theo đúng cặp `track_id + user_id`; mặc định cần 3 frame liên tiếp.
- Hai bbox cùng nhận thành một `user_id` trong cùng frame đều bị chặn bằng `identity_conflict`.
- Anti-spoofing chỉ chạy cho track vừa đạt đủ 3 frame.
- Camera trình duyệt ưu tiên 1280x720; `FACE_DET_SIZE` giữ 640.
- Box vàng hiển thị `Đang xác minh (n/3)`; chưa xác minh xong thì không hiện tên.
- Box xanh sau khi thành công hiển thị `HỌ TÊN — MÃ SINH VIÊN`, không hiện trạng thái chung, điểm similarity hoặc `user_id` nội bộ.
- Bỏ pill trạng thái xử lý ở đáy video; trạng thái quét nằm trên từng bbox.
- Sau một kết quả thành công, vòng quét phải được mở khóa ngay, không chờ safety timeout 5 giây.

## Tổng hợp review độc lập

### Accept

1. `face/yolo_arcface.py:YoloFaceDetector.detect` hiện trả toàn bộ kết quả NMS; cần sort giảm dần theo score và cắt theo cấu hình 10.
2. `static/js/camera.js` vẫn yêu cầu/capture 640x480; cần ưu tiên 1280x720 và dùng kích thước stream thực tế để tránh bóp méo ảnh.
3. `app.py:_sync_face_trackers` hiện chỉ khóa bộ đếm theo track/bbox, chưa khóa danh tính; cần reset khi cùng track đổi `user_id` và khi frame kế tiếp không còn bằng chứng hợp lệ.
4. `_handleMultiRecognitionResult` không nhả `isProcessing` sau success/duplicate; đây là độ trễ giả lên đến 5 giây.
5. `app.py:_attach_face_metadata` và `dashboard.js:renderFaceResults` đang làm mất tiến độ/nội dung danh tính do nhãn frontend ghi đè nhãn backend.
6. `templates/dashboard.html` và `camera.js` vẫn bật pill `processing-indicator`; cần loại khỏi luồng quét.
7. Cần giữ nhãn success xanh ổn định trong thời gian ngắn cho cùng track ở frontend để frame kế tiếp không lập tức nhấp nháy về vàng.
8. Cần bổ sung test cho cap >10, 10 track độc lập, đổi identity trên cùng track, conflict, delayed anti-spoof, UI 10 bbox và nhả processing lock.

### Reject

- Không hạ `FACE_MATCH_THRESHOLD`, `FACE_MATCH_MIN_MARGIN`, quality threshold hoặc số frame chỉ để scan nhanh hơn. Chưa có benchmark/calibration mới nên thay đổi này có thể làm tăng false accept.
- Không coi `items[0]` là “mặt tốt nhất” khi có trùng danh tính. Business rule yêu cầu block toàn bộ conflict, không chọn một bbox thắng.

### Defer — chỉ làm sau benchmark video thật 5–10 người

- Batch ArcFace inference: có tiềm năng giảm CPU nhưng còn phụ thuộc input batch động/tĩnh của ONNX hiện dùng.
- Thay tracker IoU bằng Hungarian/ByteTrack: chỉ thực hiện nếu benchmark cho thấy đổi `track_id` khi người đi chéo/che khuất nhau.
- Tăng `FACE_DET_SIZE` trên 640: chỉ thực hiện nếu 1280x720 vẫn miss nhiều mặt nhỏ và CPU còn dư.

## Thay đổi theo file

1. `config.py`, `config.example.py`
   - Thêm `FACE_MAX_DETECTIONS = 10`.
   - Giữ `FACE_DET_SIZE = 640`, `RECOGNITION_REQUIRED_FRAMES = 3`.

2. `face/yolo_arcface.py`
   - Thêm helper giới hạn detection có thể unit test độc lập.
   - Sau NMS: sort theo `score` giảm dần, lấy `[:max_detections]`.
   - Truyền max qua constructor detector.
   - Cập nhật mô tả tracker: mục tiêu tối đa 10 mặt, IoU đơn giản có giới hạn khi che khuất/đi chéo.

3. `face/recognition.py`
   - Import `FACE_MAX_DETECTIONS` và truyền vào `YoloFaceDetector`.
   - Không đổi threshold/model/input size trong bước này.

4. `app.py`
   - State verification lưu cả `track_id`, `user_id`, bbox và count.
   - Tăng count chỉ khi track, identity và IoU đều liên tục; khác identity/mất bằng chứng thì reset.
   - Dữ liệu gọi `_sync_face_trackers` phải mang cả `user_id` và bbox.
   - `verifying` sinh `display_label = Đang xác minh (n/3)`.
   - `ok`/`duplikat` có data danh tính sinh label `nama — nim`; không thêm score.
   - Giữ `identity_conflict` và anti-spoofing deferred như hiện tại.

5. `static/js/camera.js`
   - `getUserMedia` ưu tiên 1280x720; canvas lấy `videoWidth/videoHeight`, fallback 1280x720.
   - Bỏ cập nhật/bật pill xử lý toàn cục.
   - Không gọi overlay success cũ che video; vẫn giữ toast và refresh bảng.
   - Nhả `isProcessing` trên mọi nhánh multi-face đã xử lý.

6. `static/js/dashboard.js`
   - Ưu tiên `result.display_label` từ backend.
   - Giữ box vàng cho `warning`, xanh cho `recognized`.
   - Cache ngắn kết quả xanh theo `track_id`; nếu frame kế tiếp cùng track đang verify lại thì giữ tên xanh, nhưng không giữ bbox khi mặt đã biến mất.

7. `templates/dashboard.html`
   - Xóa `processing-indicator` khỏi camera container.
   - Tăng query version JS để trình duyệt không dùng bundle cũ.

8. Tests
   - Python: top 10 theo score sau NMS/helper.
   - Python: 10 `track_id + user_id` đạt 3 frame độc lập.
   - Python: cùng track đổi identity phải đếm lại từ 1.
   - Python: 2 mặt trùng identity bị block/reset; 8 mặt còn lại không bị ảnh hưởng.
   - Python: anti-spoof chỉ gọi khi đủ frame.
   - Python: success/duplicate label có name + NIM, không có score/user id.
   - JS: render 10 results; yellow progress; green identity; không ghi đè display label.
   - JS: success/duplicate multi-face nhả processing lock ngay.
   - JS: mapping bbox 1280x720.

## Acceptance criteria

- `results.length <= 10` cho mọi frame, đúng 10 score cao nhất nếu input >10.
- 10 người khác nhau có count độc lập và có thể cùng hoàn tất ở frame thứ 3.
- Cùng track đổi identity không được kế thừa count cũ.
- Conflict cùng frame không ghi attendance cho các bbox xung đột.
- `check_face` không chạy ở frame 1–2 và chỉ chạy trên các track đạt frame 3.
- Camera yêu cầu 1280x720, backend vẫn infer detector ở 640.
- Trong lúc scan không có pill xử lý dưới video.
- Box vàng chỉ hiện tiến độ xác minh; box xanh hiện tên + mã sinh viên, không hiện score hoặc ID nội bộ.
- Multi-face success/duplicate không làm scanner đứng 5 giây.
- Toàn bộ Python regression/pipeline và JS camera/overlay tests vượt qua.

## Chỉ số benchmark sau build

- `detector_latency_ms`, `embedding_latency_ms`, `pipeline_latency_ms` ở các mức 1, 5, 10 mặt.
- Thời gian từ frame đầu đến kết quả xác minh thành công.
- Tỷ lệ `face_too_small`, `unknown`, `identity_conflict`, đổi `track_id` trên video thật.
- So sánh 640x480 và 1280x720 ở cùng khoảng cách/ánh sáng trước khi đổi thêm model hoặc threshold.
