# Checklist chất lượng đăng ký khuôn mặt và gallery realtime

## Phạm vi

Kiểm tra luồng nhập thông tin sinh viên, thu thập 24 ảnh có kiểm soát, tạo manifest,
chọn tối đa 12 vector ArcFace và tác động tới nhận diện realtime. Các kiểm tra dùng
ngưỡng cấu hình hiện hành; không tự khẳng định accuracy hoặc FPS khi chưa có bộ dữ
liệu khuôn mặt được phê duyệt.

| ID | Hành vi quan sát được | Loại | Ưu tiên | Dữ liệu/trạng thái cần có |
|---|---|---|---:|---|
| ENR-FORM-01 | Thiếu họ tên, mã sinh viên hoặc lớp thì không bật quy trình chụp | âm/UI | P0 | Bỏ trống lần lượt từng trường |
| ENR-FORM-02 | Mã sinh viên đã thuộc người/lớp khác bị từ chối và không ghi thêm ảnh | âm/an toàn | P0 | DB test có NIM trùng |
| ENR-IMG-01 | Base64 sai, ảnh không đọc được hoặc frame rỗng bị từ chối | âm/API | P0 | Payload hỏng |
| ENR-FACE-01 | Không có mặt nào phát hiện → reject `face_count`; nhiều mặt → chỉ chọn mặt gần tâm oval nhất (xem ENR-GUIDE) | âm/ML | P0 | Mock detector (xem ENR-GUIDE) |
| ENR-QLT-01 | Mặt quá nhỏ, tối, sáng hoặc mờ bị từ chối với hướng dẫn tiếng Việt phù hợp | âm/ML/UI | P0 | Fixture theo từng quality reason, TBD (cần BA cấp) |
| ENR-QLT-02 | Landmark sai hoặc mặt/crop ra ngoài frame không được lưu | âm/biên | P0 | Mock detector/fixture |
| ENR-POSE-01 | Sáu ảnh đầu chỉ được nhận khi người dùng nhìn thẳng trong ngưỡng cấu hình | dương/biên | P0 | Mock yaw trong/ngoài biên |
| ENR-POSE-02 | Năm ảnh trái chỉ được nhận khi yaw đạt hướng và biên yêu cầu | dương/âm | P0 | Mock yaw trái/giữa/phải |
| ENR-POSE-03 | Năm ảnh phải chỉ được nhận khi yaw đạt hướng và biên yêu cầu | dương/âm | P0 | Mock yaw phải/giữa/trái |
| ENR-DIST-01 | Bốn ảnh gần chỉ được nhận khi tỷ lệ khuôn mặt đạt vùng gần nhưng chưa vượt vùng quá gần | dương/biên | P0 | Mock bbox theo tỷ lệ cấu hình |
| ENR-DIST-02 | Bốn ảnh xa chỉ được nhận trong vùng xa; quá xa hoặc còn quá gần có chỉ dẫn sửa vị trí | dương/biên | P0 | Mock bbox theo tỷ lệ cấu hình |
| ENR-STABLE-01 | Mỗi stage phải có đủ số frame hợp lệ liên tiếp trước ảnh đầu tiên được lưu | dương/âm | P0 | Chuỗi frame hợp lệ và lỗi xen kẽ |
| ENR-PROGRESS-01 | UI chỉ tăng tiến độ theo `accepted` do server trả; `retry` không tăng số ảnh | contract/UI | P0 | Mock API `retry`/`ok` |
| ENR-SEQUENCE-01 | Server tự quyết định thứ tự center → left → right → near → far, không tin stage/index từ browser | an toàn/API | P0 | Payload sửa index/stage |
| ENR-SAVE-01 | Ảnh được crop theo bbox có padding, không crop cố định giữa frame | dương/ML | P0 | Mặt lệch tâm nhưng còn trong frame |
| ENR-MANIFEST-01 | Mỗi ảnh đạt chuẩn có entry gồm file, stage, thời gian, quality metrics và crop bbox | dữ liệu | P0 | Dataset tạm thời |
| ENR-MANIFEST-02 | Manifest hỏng bị fail-closed; không trộn âm thầm dữ liệu mới với ảnh legacy không manifest | âm/an toàn | P0 | JSON hỏng và folder legacy |
| ENR-COMPLETE-01 | Chỉ đủ 24 ảnh đúng phân bố 6/5/5/4/4 mới bắt đầu cập nhật gallery | end-to-end | P0 | Session enrollment hoàn chỉnh |
| GAL-VALID-01 | Trainer bỏ ảnh không đọc được hoặc không có đúng một mặt | âm/ML | P0 | Mock `_faces_from_frame` |
| GAL-SELECT-01 | Mỗi sinh viên có tối đa 12 vector; ưu tiên đủ các pose và loại vector trùng chính xác | dữ liệu/hiệu năng | P0 | Candidate embeddings mock |
| GAL-LEGACY-01 | Dataset legacy vẫn train được; gallery schema 2 và 3 đều được recognition loader chấp nhận | tương thích | P0 | Gallery/ảnh legacy mock |
| RT-MARGIN-01 | Match vượt threshold nhưng quá sát ứng viên thứ hai được gắn `ambiguous` và không ghi điểm danh | âm/an toàn | P0 | Gallery mock hai identity gần nhau |
| RT-LOW-01 | Frame dưới ngưỡng chất lượng cứng vẫn bị từ chối; không hạ threshold để ép nhận diện | âm/an toàn | P0 | Fixture mặt mờ/nhỏ |
| RT-CONSIST-01 | Chỉ ghi điểm danh sau đủ số frame nhận diện liên tiếp theo cấu hình | realtime | P0 | Chuỗi prediction mock |
| RT-PERF-01 | Gallery sau train có không quá 12 phép so khớp template/người thay vì tối đa 50 trước đây | benchmark | P1 | Dataset test nhiều người |
| UX-01 | Mỗi stage hiển thị một hướng dẫn ngắn, đúng hành động; feedback lỗi không tắt camera | UI | P0 | Browser/camera hoặc mock fetch |
| UX-02 | Chuyển stage có khoảng dừng dễ nhận biết; hoàn tất thì dừng camera và thông báo cập nhật gallery | UI | P1 | Browser/camera |
| GAP-1.1 | FOTO_PER_USER tùy chỉnh (vd 10 hoặc 15) vẫn hoàn tất manifest và cập nhật gallery | âm/cấu hình | P0 | Environment config `FOTO_PER_USER=10` |
| GAP-1.2 | Sinh viên cũ thiếu manifest được popup gợi ý làm mới và dùng `reset_legacy` đăng ký mới | âm/UX | P0 | Dataset folder legacy không có manifest |
| GAP-2.1 | Xóa toàn bộ sinh viên tự động dọn dẹp file binary `.npz` và reload memory gallery | an toàn/dữ liệu | P0 | Xóa hết sinh viên trong DB/dataset |
| GAP-2.2 | Rebuild gallery ngầm khi xóa sinh viên đăng ký trạng thái đầy đủ cho UI polling | realtime/UI | P1 | Async background rebuild |
| GAP-3.1 | Ca học nối tiếp trong thời gian ân hạn tự động chọn ca học đang diễn ra chính thức | nghiệp vụ/lịch | P0 | Cặp ca học 08:00–10:00 và 10:00–12:00 lúc 10:15 |
| GAP-3.2 | WebSocket `process_frame` kiểm tra `admin_id in session` và ngắt khi hết hạn phiên | bảo mật/WS | P0 | WebSocket client không có session |
| GAP-3.3 | Tracker liên tục chỉ reset sau khi anti-spoofing xác nhận mặt thật và catat DB thành công | realtime/anti-spoof | P1 | Chuỗi frame với anti-spoofing deferred/failed |
| GAP-4.1 | Chuỗi văn bản báo lỗi backend và nhãn chất lượng hiển thị bằng tiếng Việt chuẩn có dấu | UI/bản địa hóa | P1 | Exception & error payloads |

---

## Multi-Face Guide Selection (ENR-GUIDE)

Khi khung hình có ≥1 mặt, hệ thống tính khoảng cách chuẩn hóa từ tâm mỗi mặt
tới tâm oval hướng dẫn. Chỉ mặt nằm trong oval (guide_distance ≤ 1.0) mới là
ứng viên; mặt gần tâm nhất được chọn để kiểm tra quality/pose.

| Ref | `_select_detection_in_guide` | [`enrollment.py` L150-171](file:///E:/TMU%20UNIVERSITY/MACHINE%20LEARNING/SOURCE%201_%C6%AFU%20TI%C3%8AN/Absensi/face/enrollment.py#L150-L171) |
|---|---|---|
| Ref | `validate_enrollment_frame` | [`enrollment.py` L174-214](file:///E:/TMU%20UNIVERSITY/MACHINE%20LEARNING/SOURCE%201_%C6%AFU%20TI%C3%8AN/Absensi/face/enrollment.py#L174-L214) |
| Test | Existing coverage | [`test_enrollment_pipeline.py` L100-112](file:///E:/TMU%20UNIVERSITY/MACHINE%20LEARNING/SOURCE%201_%C6%AFU%20TI%C3%8AN/Absensi/tests/test_enrollment_pipeline.py#L100-L112) |

| ID | Hành vi quan sát được | Loại | Ưu tiên | Auto | Dữ liệu/trạng thái cần có |
|---|---|---|---:|---|---|
| ENR-GUIDE-01 | 1 mặt duy nhất nằm trong oval → mặt đó được chọn, accepted nếu đạt quality+pose | dương/core | P0 | Yes | Mock 1 detection bbox center trong oval |
| ENR-GUIDE-02 | Nhiều mặt, chỉ 1 mặt trong oval → chọn đúng mặt trong oval, mặt ngoài bị bỏ qua | dương/multi | P0 | Yes | Mock 2 detections: 1 center + 1 edge |
| ENR-GUIDE-03 | Nhiều mặt, ≥2 mặt trong oval → chọn mặt gần tâm oval nhất (guide_distance nhỏ nhất) | dương/multi | P0 | Yes | Mock 3 detections đều trong oval, khoảng cách khác nhau |
| ENR-GUIDE-04 | Nhiều mặt, 0 mặt trong oval → reject reason=`face_outside_guide`, message hướng dẫn di chuyển mặt vào khung | âm/multi | P0 | Yes | Mock 2 detections bbox ngoài oval |
| ENR-GUIDE-05 | 0 mặt phát hiện (detector trả []) → reject reason=`face_count`, không trả `face_outside_guide` | âm/zero | P0 | Yes | Mock detector trả [] |
| ENR-GUIDE-06 | Detection có bbox width ≤ 0 hoặc height ≤ 0 → bị bỏ qua, không crash | biên/robustness | P1 | Yes | Mock detection (0, 200, 0, 150) |
| ENR-GUIDE-07 | Mặt đúng biên oval (guide_distance = 1.0) → vẫn được chọn (≤ 1.0 chứ không <) | biên/BVA | P0 | Yes | Mock detection sao cho guide_distance == 1.0 |
| ENR-GUIDE-08 | Mặt vượt biên oval sát (guide_distance = 1.001) → bị loại, không được chọn | biên/BVA | P0 | Yes | Mock detection sao cho guide_distance > 1.0 vừa đủ |
| ENR-GUIDE-09 | Detection bbox gây TypeError/ValueError khi unpack → bị skip, không crash toàn request | biên/error | P1 | Yes | Mock detection bbox = None hoặc "abc" |
| ENR-GUIDE-10 | Mặt được chọn trong oval nhưng fail quality (mờ/tối/nhỏ) → reject reason là quality, không phải guide | âm/composite | P0 | Yes | Mock detection trong oval + mock measure_quality trả fail |
| ENR-GUIDE-11 | Mặt được chọn trong oval đạt quality nhưng sai pose cho stage hiện tại → reject reason là pose | âm/composite | P0 | Yes | Mock detection trong oval, yaw sai stage |

## Tiêu chí dừng

- P0 tự động phải xanh trước khi review camera thủ công.
- Không chấp nhận finding yêu cầu hạ `FACE_MATCH_THRESHOLD` nếu chưa hiệu chuẩn.
- Test camera thật, accuracy, latency và chống giả cần fixture/thiết bị có đồng ý sử dụng; nếu chưa có ghi `TBD (cần BA cấp)`.

