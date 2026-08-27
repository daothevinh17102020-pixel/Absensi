# Theo doi sua loi scan khuon mat

## Pham vi da duoc phe duyet

- Su dung cho demo dai hoc, phi thuong mai.
- Chay inference tren laptop Intel CPU; khong dung GPU, Railway, hay Vercel.
- Thay Haar Cascade + LBPH bang InsightFace `buffalo_l` (detector + ArcFace embedding).
- Hien thi box theo tung khuon mat: xanh = da nhan dien, vang = dang xac minh/chua hieu chuan, do = khong khop, gia mao, hoac xung dot danh tinh.

## Hien trang truoc khi sua

- Dataset hien co: 3 sinh vien (ID 7, 8, 9), moi nguoi 50 anh.
- Engine cu: Haar Cascade + LBPH, `trainer.yml`.
- Backend da tra `bbox` cho tung mat, nhung giao dien chi co status overlay va chua ve bbox tren live video.
- Baseline da chay trong `.venv`: 29 unit/regression tests pass, 3 DB integration tests skip theo cau hinh.

## Nhat ky cap nhat

### Buoc 1 - Hoan thanh phan code

- Tao context nay va them InsightFace 0.7.3 + ONNX Runtime 1.23.2 CPU.
- Da xac minh runtime import duoc InsightFace + ONNX Runtime trong `.venv` ma van giu NumPy 1.26.4 va OpenCV 4.8.1.
- Model asset `buffalo_l` can duoc tai mot lan vao `models/insightface/`; lan tai trong khi sua bi dung do toc do mang qua cham. Chay `test_setup.py` khi co ket noi on dinh de tai lai; engine se bao loi ro rang thay vi treo camera khi model chua co.

### Buoc 2 - Hoan thanh phan code, cho model asset

- `face.recognition.predict()` da dung detector InsightFace va cosine matching tung khuon mat.
- `face.trainer.train_model()` da tao gallery embedding atomically, chi nhan anh co dung mot khuon mat va ghi ly do loai anh vao `models/face_gallery.json`.
- Gallery 3 x 50 anh se duoc tao ngay khi download model ket thuc va goi train_model.

### Buoc 3 - Hoan thanh

- Ve bbox/nhan tung khuon mat tren live video, xu ly mirror va `object-fit: cover`.
- API `results[]` bo sung `bbox`, `match_score`, `display_status`, va `display_label` cho moi khuon mat.

### Buoc 4 - Can test truc tiep

- Thu 3 sinh vien o goc/anh sang khac, 1 nguoi la, va 1 frame co tu 2 nguoi.
- Hieu chuan `FACE_MATCH_THRESHOLD` tu cac score thuc te truoc khi mo tu dong ghi diem danh.

### Buoc 5 - Hoan thanh regression

- 31 unit/regression tests pass; 3 DB integration tests skip theo cau hinh.
- 2 JS tests pass: multi-face transport va mapping bbox mirror/crop.

## An toan va hieu chuan

- Khi `FACE_MATCH_THRESHOLD` chua duoc dat, engine chi hien `Can hieu chuan`; khong cho tu dong ghi diem danh.
- Khong co fallback tu dong ve LBPH neu InsightFace/model asset loi.
- Anti-spoofing LBP giu trang thai tat mac dinh vi chua co du lieu hieu chuan.
