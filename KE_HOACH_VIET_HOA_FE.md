# Runbook phối hợp Việt hóa FE Absensi

## Mục tiêu và ranh giới

Việt hóa toàn bộ nội dung người dùng nhìn thấy trong 16 template đang hoạt động, `static/js/camera.js`, `static/js/dashboard.js` và các chuỗi hiển thị từ `app.py`. Không sửa `templates/stitch`, database, mô hình ML, giao thức camera/ESP32, route, schema hoặc API contract.

Giữ nguyên tuyệt đối các giá trị máy `hadir`, `terlambat`, `izin`, `sakit`, `alpha`, `Senin`…`Minggu`, field name, ID, URL, JSON key, CSS class và điều kiện Jinja/JavaScript. Chỉ ánh xạ chúng sang tiếng Việt tại tầng hiển thị.

## Phân công

- **Codex chính:** baseline, inventory, hợp đồng thuật ngữ, tích hợp diff, xử lý `app.py`, test, phân loại finding và nghiệm thu.
- **Codex CLI:** sửa tuần tự từng batch template/JS theo allowlist; không sửa backend, test, CSS hoặc Stitch.
- **Agy CLI:** reviewer nội dung/checklist chỉ đọc; không sửa file và không quyết định kỹ thuật.

## Trình tự thực thi

### 0. Baseline và phục hồi

- Ghi `git status --short`, file tracked/untracked, SHA-256 của file mục tiêu và lưu bản sao ngoài repository.
- Chụp lại baseline trước từng batch và so sánh đường dẫn/hash sau batch.
- Khi batch lỗi, chỉ phục hồi đúng file từ bản sao hoặc `git restore -- <đường-dẫn-chính-xác>` nếu file đó sạch trước batch.
- Không dùng `git reset --hard`, `git checkout .` hoặc lệnh phục hồi toàn repository.

### 1. Hợp đồng bản địa hóa

- Inventory `Translate`: text node, title, placeholder, aria-label, confirm, toast, `flash`, `pesan`, `display_label`.
- Inventory `Preserve`: machine value, field, ID, route, URL, JSON key, class, Jinja/JS condition.
- Mapping hiển thị: `hadir → Có mặt`, `terlambat → Đi muộn`, `izin → Vắng có phép`, `sakit → Nghỉ ốm`, `alpha → Vắng không phép`.
- Ngày Indonesia chỉ đổi nhãn lúc render; không đổi `_get_nama_hari()` hoặc dữ liệu truy vấn.
- `str(e)` giữ nguyên; literal dành cho người dùng được dịch; câu nội suy chỉ dịch phần văn bản bao quanh.

### 2. Codex CLI theo batch không chồng lấn

1. Batch A: `templates/base.html`, `templates/login.html`, `templates/register_admin.html`.
2. Batch B: ba template `kelas`, `templates/matakuliah/form.html`, hai template `jadwal`.
3. Batch C: `templates/dashboard.html`, hai template `absensi`, `templates/laporan/index.html`.
4. Batch D: ba template `mahasiswa`.
5. Batch E: `static/js/camera.js`, `static/js/dashboard.js`.

Mỗi prompt phải ghi allowlist chính xác, invariant, yêu cầu dừng nếu cần file ngoài phạm vi và báo cáo mọi file đã sửa. Codex chính review delta và compile template sau từng batch rồi mới mở batch kế tiếp.

Mẫu gọi:

```powershell
$workspace = 'E:\TMU UNIVERSITY\MACHINE LEARNING\SOURCE 1_ƯU TIÊN\Absensi'
$codexCli = 'C:\Users\vinh2\AppData\Roaming\npm\codex.cmd'
$prompt | & $codexCli exec --ephemeral --sandbox workspace-write --cd $workspace -
```

Không dùng bypass, `--add-dir` hoặc chạy batch song song.

### 3. Chuỗi Flask và mapping hiển thị

Codex chính Việt hóa `flash`, literal `pesan`, `display_label` và mapping presentation-boundary. Giữ nguyên key, mã `status`/`tipe`, HTTP status, exception passthrough và toàn bộ hành vi BE.

### 4. Test phụ thuộc nội dung

Chỉ cập nhật assertion copy-dependent khi chuỗi nguồn tương ứng đã đổi. Không bỏ test hoặc làm yếu assertion logic. Review riêng `tests/test_regressions.py` và `tests/test_camera_multi.js`.

### 5. Kiểm thử

- Compile đủ 16 template bằng Jinja loader.
- `python -m unittest discover -s tests -p "test_regressions.py"` khi `RUN_DB_TESTS` không đặt.
- `node tests/test_camera_multi.js`.
- `node tests/test_face_overlay.js`.
- Quét lại inventory Translate/Preserve.
- Manual route matrix chỉ dùng mock/test data; không tạo hoặc xóa dữ liệu thật.
- DB integration chỉ chạy nếu phát hiện thay đổi query/lookup ngoài dự kiến và phải dùng database test cô lập.

### 6. Agy review và nghiệm thu

Agy trả `file`, `line/context`, `current copy`, `suggested copy`, `reason`, `confidence`. Codex chính gắn từng finding là `Accept`, `Reject` hoặc `Defer`, áp dụng tối thiểu các finding được chấp nhận và chạy lại toàn bộ kiểm thử.

## Definition of Done

- 16/16 template compile thành công.
- Python regression và hai test Node đạt 100%.
- Không có thay đổi ngoài phạm vi so với baseline.
- Không còn chuỗi Indonesia/Anh trong inventory Translate, trừ mục Defer có lý do.
- Machine token trong inventory Preserve không đổi.
- 100% finding của Codex CLI/Agy được phân loại.
- Mọi dirty edit có trước task được bảo toàn.

## Nhật ký thực thi và nghiệm thu

- Baseline/backup phục hồi: `C:\Users\vinh2\AppData\Local\Temp\absensi_viet_hoa_a9ef227a9dca4e2d83ffcdfa7c44f5a2`.
- Năm batch Codex CLI hoàn thành tuần tự, không có đường dẫn ngoài allowlist bị sửa.
- Inventory `Translate`: 16 template hoạt động; toast/trạng thái trong hai file JS; `flash`, biến `error`, literal `pesan`, `display_label` và tiêu đề cột export trong `app.py`.
- Inventory `Preserve`: route/endpoint, field/ID/key/class, điều kiện Jinja/JS, `_get_nama_hari()`, `on/off`, `status`/`tipe`, HTTP status và các token `hadir`, `terlambat`, `izin`, `sakit`, `alpha`, `Senin`…`Minggu`.

### Ma trận màn hình

| Template | Route chính | Auth | Fixture tối thiểu | Kỳ vọng |
|---|---|---|---|---|
| `base.html` | dùng chung | tùy trang | session + kết quả tìm kiếm mock | menu/tìm kiếm tiếng Việt; thứ được ánh xạ khi hiển thị |
| `login.html` | `/login` | không | admin mock | đăng nhập/validation tiếng Việt |
| `register_admin.html` | `/register` | không | chưa có admin | đăng ký quản trị tiếng Việt |
| `dashboard.html` | `/` | có | thống kê + điểm danh mock | camera, trạng thái và bảng tiếng Việt |
| `kelas/index.html` | `/kelas` | có | danh sách lớp mock | danh sách/bộ lọc/modal tiếng Việt |
| `kelas/form.html` | `/kelas/tambah`, `/kelas/edit/<id>` | có | lớp mock khi sửa | form/nút/lỗi tiếng Việt |
| `kelas/detail.html` | `/kelas/<id>/matakuliah` | có | lớp + môn học mock | chi tiết/modal tiếng Việt |
| `matakuliah/form.html` | `/matakuliah/tambah`, `/matakuliah/edit/<id>` | có | lớp + môn học mock | form/nút/lỗi tiếng Việt |
| `jadwal/index.html` | `/jadwal` | có | lịch mock | ngày được ánh xạ; giá trị máy giữ nguyên |
| `jadwal/form.html` | `/jadwal/tambah` | có | môn/lớp mock | option hiển thị tiếng Việt, value Indonesia |
| `absensi/manual.html` | `/absensi/manual` | có | điểm danh mock | năm trạng thái tiếng Việt |
| `absensi/rekap.html` | `/absensi/rekap` | có | rekap/ringkasan mock | bộ lọc, bảng, export tiếng Việt |
| `laporan/index.html` | `/laporan` | có | thống kê báo cáo mock | biểu đồ/xếp hạng tiếng Việt |
| `mahasiswa/index.html` | `/mahasiswa` | có | sinh viên/lớp mock | bảng/bộ lọc/modal tiếng Việt |
| `mahasiswa/register.html` | `/mahasiswa/register` | có | lớp mock | form, máy ảnh, tiến trình tiếng Việt |
| `mahasiswa/edit.html` | `/mahasiswa/edit/<id>` | có | sinh viên/lớp mock | form/nút/lỗi tiếng Việt |

### Phân loại finding Agy CLI

| Finding | Kết quả | Lý do |
|---|---|---|
| Header export còn `Hari/Tanggal/Waktu Absen/Status/Keterangan` | Accept | Chuỗi xuất hiện trong CSV/XLSX và thuộc tầng hiển thị. |
| Điều kiện thông báo camera dùng `aktif` thay vì trạng thái hiện có | Accept | Có bằng chứng trực tiếp; sửa theo boolean `camera_state['active']`, không đổi protocol. |
| Ngày Indonesia hiển thị trực tiếp trong kết quả tìm kiếm | Accept | Cần ánh xạ tại render boundary. |
| Hai header bảng còn `NIM` | Accept | Chuẩn hóa thành `Mã sinh viên`. |
| Năm tiêu đề toast viết hoa kiểu tiếng Anh | Accept | Chuẩn hóa sentence case tiếng Việt. |
| Placeholder kết nối ghi nhầm trạng thái chống giả mạo | Accept | Đúng phần tử `connection-status`; đổi thành `Đang kết nối...`. |
| Nút XLSX ghi `Tải báo cáo` | Accept | Chuẩn hóa rõ với nút `Xuất CSV` thành `Xuất Excel`. |

Không có finding `Reject` hoặc `Defer`.

### Kết quả gate cuối

- Jinja: 16/16 template compile thành công.
- Python: 31 test đạt, 3 DB integration test được skip đúng kế hoạch.
- Node: `test_camera_multi.js` và `test_face_overlay.js` đạt.
- JavaScript syntax và `git diff --check`: đạt.
- Hash các file dirty/untracked có trước nhưng ngoài phạm vi: không thay đổi so với backup.
