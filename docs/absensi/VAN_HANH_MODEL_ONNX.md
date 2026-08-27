# Van hanh model ONNX

1. Dat detector ONNX da duoc cap quyen tai
   `models/yolo/yolov8n-face-5kps.onnx`, hoac dat bien moi truong
   `FACE_DETECTOR_MODEL_PATH`. File phai tra output decoded
   `[cx, cy, w, h, score, 10 landmarks]`; health check tu choi raw YOLO head
   hay detector khong co nam landmarks de tranh box/alignment sai.
2. Dat ArcFace ONNX da duoc cap quyen tai `models/arcface/w600k_r50.onnx`,
   hoac dat `FACE_RECOGNITION_MODEL_PATH`.
3. Dien checksum va thong tin quyen su dung vao ban sao noi bo cua
   `models/MODEL_MANIFEST.example.json`.
4. Chay `.venv\Scripts\python.exe test_setup.py`. Lenh nay chi health-check
   assets local, khong tai model tu Internet.
5. Chay lai `train_model()` de tao gallery schema 2, sau do hieu chuan
   `FACE_MATCH_THRESHOLD` bang mau anh cua dung model. Khi threshold chua co,
   app van ve box nhung fail-closed va khong tu ghi diem danh.
