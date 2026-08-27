# Đặc tả kiểm thử API Absensi

Không gọi production API và không đọc secret. Runner dùng Flask test client, session/DB/filesystem/model được mock hoặc thư mục tạm cô lập.

| API | Test case | Ca kiểm thử chính | Status/schema mong đợi | Trạng thái chạy |
|---|---|---|---|---|
| `GET /api/search` | TC-AUTH-01, TC-API-02 | auth, query rỗng, có kết quả, DB lỗi | 401/200/5xx; `{status,data,pesan}` | Có thể chạy local |
| `GET /api/mahasiswa/list` | TC-AUTH-01, TC-API-02 | auth, DB success/failure | 401/200/5xx; JSON ổn định | Có thể chạy local |
| `GET /api/jadwal/hari-ini` | TC-AUTH-01, TC-API-02 | auth, empty/success/failure | 401/200/5xx; giữ ngày máy | Có thể chạy local |
| `GET /api/absensi/hari-ini` | TC-AUTH-01, TC-API-02 | auth, success/failure | 401/200/5xx | Có thể chạy local |
| `POST /api/absensi/manual` | TC-MAN-01 | JSON shape/type, ID/status, lớp/ngày, insert/update | 400/404/409 hoặc 200 theo contract hiện có | Có thể chạy local |
| `POST /api/foto/upload` | TC-UP-01, TC-UP-02 | field/type/base64/image/index/duplicate | 400/409/500/200; không ghi ngoài temp | Có thể chạy local |
| `POST /api/training/start` | TC-TRN-01 | lock bận/start | 409/202 hoặc contract hiện có | Chỉ mock thread/model |
| `POST /api/absensi/proses` | TC-REC-01, TC-MODEL-01 | frame/client ID/model unavailable | 400/503/200 | Chỉ mock CV/ML |
| `POST /api/camera/toggle` | TC-CAM-01, TC-CAM-02 | boolean/type/client isolation | 400/200 | Có thể chạy local |
| `GET /absensi/export` | TC-EXP-01, TC-EXT-01 | format và bốn filter | CSV/XLSX đúng filter | Có thể chạy local |

Các luồng Google Form/Drive không có callable API hoặc contract trong repository nên trạng thái là `pending`; không tạo giả endpoint, field, credential hay kết quả.

## Kết quả thực thi 2026-08-26

- Flask/Python regression: 41 test chạy, 38 đạt và 3 DB integration test skip đúng chủ đích.
- Node UI: `test_camera_multi.js` và `test_face_overlay.js` đạt.
- Jinja: 16/16 template compile.
- Python/JavaScript syntax và `git diff --check`: đạt.
- Không gọi database production, camera vật lý, ESP32, Google Form/Drive hoặc API bên ngoài.
- Codex CLI: 11 finding ban đầu; sau hai vòng fix/re-audit, 11/11 đã đóng. Finding cuối về lộ exception khi upload ảnh được sửa và có regression test.
- Agy CLI: 4 omission và 3 optional improvement; tất cả `Accept` vì có evidence và chỉ ảnh hưởng traceability tài liệu. Không có `Reject`/`Defer`.
