# Test case chất lượng đăng ký khuôn mặt và gallery realtime

## Quy ước

- Mọi ngưỡng lấy từ `config.py` của môi trường test, không ghi đè bằng giá trị suy đoán.
- Ảnh/video khuôn mặt thật: `TBD (cần BA cấp)` và phải có đồng ý sử dụng.
- Test tự động dùng mock/synthetic data; test camera thật được đánh dấu manual.

## TC-ENR-01 — Kiểm tra dữ liệu form bắt buộc

- Nguồn: `ENR-FORM-01`, `ENR-FORM-02`
- Ưu tiên: P0
- Tiền điều kiện: Admin đã đăng nhập; DB test có một sinh viên mẫu do fixture tạo.
- Các bước: Lần lượt bỏ trống họ tên/NIM/lớp và nhấn bắt đầu; sau đó gửi NIM fixture với tên hoặc lớp khác.
- Kết quả mong đợi: Camera không bắt đầu khi thiếu trường; xung đột NIM trả 409; không tạo sinh viên hay ảnh mới.
- Dữ liệu test: Giá trị giả sinh bởi fixture; không dùng thông tin sinh viên thật.
- Tự động hóa: Có thể tự động hóa UI validation và API mock.

## TC-ENR-02 — Payload ảnh không hợp lệ

- Nguồn: `ENR-IMG-01`
- Ưu tiên: P0
- Tiền điều kiện: Session admin hợp lệ.
- Các bước: Gửi JSON thiếu `foto`; base64 sai; byte không decode thành ảnh; frame rỗng.
- Kết quả mong đợi: Trả 400 hoặc `retry` phù hợp; không tạo user/folder/manifest.
- Dữ liệu test: Chuỗi base64 synthetic.
- Tự động hóa: Có.

## TC-ENR-03 — Số lượng khuôn mặt

- Nguồn: `ENR-FACE-01`
- Ưu tiên: P0
- Tiền điều kiện: Detector được mock độc lập với 0, 1 và 2 detection.
- Các bước: Gửi cùng frame qua ba cấu hình detector.
- Kết quả mong đợi: 0 mặt hướng dẫn đưa mặt vào khung; 2 mặt yêu cầu chỉ để một mặt; chỉ 1 mặt được xét tiếp; progress không tăng ở hai trường hợp lỗi.
- Dữ liệu test: Mock detector; fixture camera thật `TBD (cần BA cấp)`.
- Tự động hóa: Có với mock; manual với camera.

## TC-ENR-04 — Chặn ảnh kém chất lượng

- Nguồn: `ENR-QLT-01`, `ENR-QLT-02`
- Ưu tiên: P0
- Tiền điều kiện: Cấu hình enrollment mặc định hoặc profile test đã ghi nhận.
- Các bước: Lần lượt đưa frame quá nhỏ, tối, sáng, mờ, landmark NaN, mặt ngoài frame.
- Kết quả mong đợi: Mỗi frame trả `retry` cùng `reason` chính xác và hướng dẫn tiếng Việt; không lưu ảnh.
- Dữ liệu test: Synthetic/mock; fixture thật `TBD (cần BA cấp)`.
- Tự động hóa: Có với synthetic/mock.

## TC-ENR-05 — Stage nhìn thẳng

- Nguồn: `ENR-POSE-01`
- Ưu tiên: P0
- Tiền điều kiện: Enrollment mới, accepted count bằng 0.
- Các bước: Gửi yaw ngay trong biên; tại biên; vượt biên trái và phải.
- Kết quả mong đợi: Chỉ yaw trong biên cấu hình được tính ổn định; đủ 6 ảnh mới chuyển stage trái.
- Dữ liệu test: Landmark synthetic.
- Tự động hóa: Có.

## TC-ENR-06 — Stage quay trái và phải

- Nguồn: `ENR-POSE-02`, `ENR-POSE-03`
- Ưu tiên: P0
- Tiền điều kiện: Manifest đặt tại đầu từng stage bằng fixture.
- Các bước: Với stage trái gửi yaw giữa/trái/phải; lặp lại đối xứng cho stage phải.
- Kết quả mong đợi: Chỉ đúng hướng và đủ biên được nhận; thông báo sửa hướng đúng; phân bố cuối là 5 trái và 5 phải.
- Dữ liệu test: Landmark synthetic; mapping camera mirror manual `TBD (cần BA cấp)`.
- Tự động hóa: Có cho server; manual cho câu chữ/preview mirror.

## TC-ENR-07 — Stage gần và xa

- Nguồn: `ENR-DIST-01`, `ENR-DIST-02`
- Ưu tiên: P0
- Tiền điều kiện: Manifest đặt tại đầu stage near/far.
- Các bước: Gửi bbox dưới, tại và trên mỗi biên tỷ lệ trong cấu hình.
- Kết quả mong đợi: Vùng gần nhận đúng 4 ảnh; vùng xa nhận đúng 4 ảnh; quá gần/xa có feedback đúng và không tăng progress.
- Dữ liệu test: Bbox synthetic theo kích thước frame.
- Tự động hóa: Có.

## TC-ENR-08 — Ổn định frame và reset chuỗi

- Nguồn: `ENR-STABLE-01`, `ENR-PROGRESS-01`
- Ưu tiên: P0
- Tiền điều kiện: `ENROLLMENT_STABLE_FRAMES` đã biết từ config.
- Các bước: Gửi N−1 frame tốt; chèn một frame sai; gửi lại N frame tốt; sau ảnh đầu tiếp tục frame tốt.
- Kết quả mong đợi: N−1 không lưu; frame sai reset bộ đếm; frame thứ N sau reset mới lưu; UI chỉ dùng `data.accepted` từ server.
- Dữ liệu test: Detector/quality mock.
- Tự động hóa: Có.

## TC-ENR-09 — Server kiểm soát sequence

- Nguồn: `ENR-SEQUENCE-01`
- Ưu tiên: P0
- Tiền điều kiện: Enrollment ở stage center.
- Các bước: Browser giả `index=20` hoặc stage far; gửi frame far; sau đó gửi frame center hợp lệ.
- Kết quả mong đợi: Server vẫn yêu cầu center; chỉ frame center hợp lệ được nhận.
- Dữ liệu test: HTTP client và detector mock.
- Tự động hóa: Có.

## TC-ENR-10 — Crop theo detection và manifest

- Nguồn: `ENR-SAVE-01`, `ENR-MANIFEST-01`
- Ưu tiên: P0
- Tiền điều kiện: Dataset path trỏ tới thư mục tạm.
- Các bước: Gửi mặt lệch tâm nhưng hợp lệ; hoàn thành điều kiện ổn định; đọc ảnh và manifest vừa tạo.
- Kết quả mong đợi: Crop bao quanh bbox với padding và nằm trong frame; entry manifest có file/stage/time/metrics/crop bbox; file tham chiếu tồn tại.
- Dữ liệu test: Frame synthetic có bbox lệch tâm.
- Tự động hóa: Có.

## TC-ENR-11 — Manifest hỏng và dữ liệu legacy

- Nguồn: `ENR-MANIFEST-02`, `GAL-LEGACY-01`
- Ưu tiên: P0
- Tiền điều kiện: Một folder có JSON hỏng; một folder chỉ có ảnh legacy.
- Các bước: Thử ghi enrollment mới vào từng folder; chạy trainer trên dataset legacy riêng; nạp gallery schema 2 rồi schema 3.
- Kết quả mong đợi: Ghi mới fail-closed với JSON hỏng/legacy không manifest; trainer legacy vẫn tạo gallery; loader chấp nhận schema 2 và 3.
- Dữ liệu test: File trong temp directory.
- Tự động hóa: Có.

## TC-ENR-12 — Hoàn tất đúng 24 ảnh

- Nguồn: `ENR-COMPLETE-01`
- Ưu tiên: P0
- Tiền điều kiện: DB/dataset tạm; detector trả pose theo kịch bản.
- Các bước: Hoàn thành tuần tự 6 center, 5 left, 5 right, 4 near, 4 far; thử gửi ảnh thứ 25.
- Kết quả mong đợi: Chỉ sau ảnh 24 trạng thái hoàn tất; phân bố manifest đúng; ảnh 25 không được lưu; client gọi training một lần.
- Dữ liệu test: Mock sequence.
- Tự động hóa: Có ở API; UI end-to-end manual/Playwright nếu môi trường có.

## TC-GAL-01 — Loại ảnh không dùng được

- Nguồn: `GAL-VALID-01`
- Ưu tiên: P0
- Tiền điều kiện: Dataset tạm có ảnh unreadable, 0 mặt, 2 mặt và 1 mặt hợp lệ.
- Các bước: Chạy `train_model` với `_faces_from_frame` mock theo từng file.
- Kết quả mong đợi: Chỉ ảnh có đúng một mặt thành candidate; diagnostics ghi reason cho các ảnh bị loại.
- Dữ liệu test: Temp files và mock embedding.
- Tự động hóa: Có.

## TC-GAL-02 — Chọn vector đa pose có giới hạn

- Nguồn: `GAL-SELECT-01`, `RT-PERF-01`
- Ưu tiên: P0
- Tiền điều kiện: Candidate list có đủ năm stage, chênh quality và một duplicate chính xác.
- Các bước: Chạy selector với hơn 12 candidate; đọc gallery kết quả.
- Kết quả mong đợi: Không quá 12 vector/người; không giữ duplicate chính xác; ưu tiên đại diện các stage; metadata ghi số accepted/selected.
- Dữ liệu test: Vector NumPy synthetic.
- Tự động hóa: Có.

## TC-RT-01 — Từ chối match mơ hồ

- Nguồn: `RT-MARGIN-01`
- Ưu tiên: P0
- Tiền điều kiện: Gallery mock có hai identity gần nhau; threshold/margin lấy từ config test.
- Các bước: Tạo embedding vượt threshold nhưng margin dưới yêu cầu; chạy predict.
- Kết quả mong đợi: `recognition_status=ambiguous`, có runner-up metadata, `dikenali=false`, không ghi attendance.
- Dữ liệu test: Vector synthetic.
- Tự động hóa: Có.

## TC-RT-02 — Chất lượng thấp và xác nhận nhiều frame

- Nguồn: `RT-LOW-01`, `RT-CONSIST-01`
- Ưu tiên: P0
- Tiền điều kiện: Recognition threshold đã hiệu chuẩn trong test; required frames từ config.
- Các bước: Gửi frame dưới ngưỡng quality; sau đó chuỗi identity hợp lệ ngắn hơn và bằng required frames.
- Kết quả mong đợi: Frame xấu không embed/ghi điểm danh; chuỗi thiếu frame không ghi; đủ frame mới ghi đúng một lần.
- Dữ liệu test: Mock predict/DB.
- Tự động hóa: Có.

## TC-UX-01 — Hướng dẫn và vòng lặp retry

- Nguồn: `UX-01`, `UX-02`
- Ưu tiên: P0
- Tiền điều kiện: Trang đăng ký mở trên trình duyệt hỗ trợ camera.
- Các bước: Gây lần lượt lỗi không mặt, nhiều mặt, tối, mờ, sai pose, sai khoảng cách; hoàn thành từng stage.
- Kết quả mong đợi: Một chỉ dẫn ngắn, đúng lỗi; retry không tắt camera; stage/progress đổi đúng; hoàn tất dừng camera và thông báo training.
- Dữ liệu test: Camera/fixture `TBD (cần BA cấp)`.
- Tự động hóa: Một phần bằng mock fetch; xác nhận camera manual.

## TC-PAD-01 — Giới hạn bảo mật được trình bày đúng

- Nguồn: `PAD-01`
- Ưu tiên: P0
- Tiền điều kiện: Review source/config/docs.
- Các bước: Tìm khai báo MediaPipe, MiniFASNet, deep liveness hoặc bank-grade; kiểm tra asset/model manifest.
- Kết quả mong đợi: Không tuyên bố model chưa được đóng gói; V1 được mô tả là quality/pose gate, không phải xác thực ngân hàng.
- Dữ liệu test: Repository hiện tại.
- Tự động hóa: Review tĩnh.

## TC-REG-01 — Regression quyết định điểm danh

- Nguồn: `ATT-REG-01`
- Ưu tiên: P0
- Tiền điều kiện: Bộ test regression hiện hữu.
- Các bước: Chạy các test unknown, low-confidence, duplicate identity/candidate, present/absent, manual correction và export.
- Kết quả mong đợi: Không có regression; trạng thái review/attendance không bị pipeline enrollment thay đổi ngoài contract đã nêu.
- Dữ liệu test: Theo `testcases-regression.md`.
- Tự động hóa: Có phần backend; manual cho export/UI nếu fixture thiếu.

## TC-GAP-01 — Custom FOTO_PER_USER enrollment manifest completion

- Nguồn: `GAP-1.1`
- Ưu tiên: P0
- Tiền điều kiện: `FOTO_PER_USER` đặt thành 10 trong environment.
- Các bước: Tạo manifest với 10 sample; gọi `manifest_is_complete(samples, target_total=10)`.
- Kết quả mong đợi: Hàm trả về True; API training/start cho phép tạo gallery thành công.
- Dữ liệu test: Manifest JSON 10 sample.
- Tự động hóa: Có (`test_gap_1_1_custom_foto_per_user_manifest_is_complete`).

## TC-GAP-02 — Reset legacy dataset without manifest

- Nguồn: `GAP-1.2`
- Ưu tiên: P0
- Tiền điều kiện: Sinh viên có thư mục dataset cũ chứa file `.jpg` nhưng không có `enrollment_manifest.json`.
- Các bước: Gửi request upload ảnh ban đầu không có `reset_legacy`; sau đó gửi kèm `reset_legacy=true`.
- Kết quả mong đợi: Request đầu trả 409 kèm `can_reset=True`; request sau xóa thư mục cũ và bắt đầu enrollment mới.
- Dữ liệu test: Temporary legacy dataset directory.
- Tự động hóa: Có (`test_gap_1_2_legacy_dataset_reset_option`).

## TC-GAP-03 — Empty gallery binary cleanup on total student deletion

- Nguồn: `GAP-2.1`
- Ưu tiên: P0
- Tiền điều kiện: File `face_gallery.npz` tồn tại trên đĩa từ lượt train trước.
- Các bước: Xóa toàn bộ sinh viên/ảnh khỏi dataset; gọi `train_model()`.
- Kết quả mong đợi: `train_model()` trả về False, xóa file `face_gallery.npz` khỏi đĩa và gọi `reload_model()`.
- Dữ liệu test: Empty dataset directory + dummy `.npz`.
- Tự động hóa: Có (`test_gap_2_1_empty_profiles_deletes_npz_and_reloads_gallery`).

## TC-GAP-04 — Schedule grace period overlap resolution

- Nguồn: `GAP-3.1`
- Ưu tiên: P0
- Tiền điều kiện: Có 2 ca học cho cùng lớp (Ca 1: 08:00–10:00, Ca 2: 10:00–12:00); giờ hiện tại 10:15 (Ca 1 đang trong grace period 30m, Ca 2 đang học chính thức).
- Các bước: Gọi `_select_active_schedule_for_user(user, jadwal_list, None)`.
- Kết quả mong đợi: Chọn chính xác Ca 2 (thời gian học chính thức), không trả lỗi `multiple_active_schedules`.
- Dữ liệu test: Mock jadwal list.
- Tự động hóa: Có (`test_gap_3_1_select_active_schedule_strict_time_matching`).

## TC-GAP-05 — WebSocket process_frame session authentication

- Nguồn: `GAP-3.2`
- Ưu tiên: P0
- Tiền điều kiện: WebSocket client kết nối nhưng không có `admin_id` trong Flask session.
- Các bước: Gửi sự kiện `process_frame`.
- Kết quả mong đợi: Trả về kết quả status `error` với thông báo `Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.`
- Dữ liệu test: Test request context.
- Tự động hóa: Có (`test_gap_3_2_websocket_process_frame_requires_admin_session`).

