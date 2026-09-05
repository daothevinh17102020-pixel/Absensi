# Sistem Absensi Face Recognition — Project Rules

## Konteks Proyek
Sistem absensi berbasis face recognition menggunakan Python 3.10 + Flask + 
MySQL + OpenCV LBPH. Baca context.md untuk spesifikasi lengkap sebelum 
menulis kode apapun.

## Aturan Wajib
- Gunakan Python 3.10, bukan versi lain
- Semua query database HANYA di database.py
- Semua konfigurasi HANYA di config.py, tidak boleh hardcode nilai
- Semua route kecuali /login dan /register wajib @login_required
- Komentar kode dalam Bahasa Indonesia
- Response API selalu JSON: {"status":"ok/error","data":...,"pesan":...}
- Error handling wajib try/except di semua fungsi database
- Training LBPH wajib di background thread, tidak boleh blokir Flask
- UNIQUE constraint absensi: (user_id, jadwal_id, tanggal)
- Jangan pernah sentuh config.py, dataset/, models/ untuk di-commit
- **Quy tắc giải trình 4 điểm trước khi sửa code (FE & BE)**:
  Trước khi chỉnh sửa bất kỳ file code FE hay BE nào, bắt buộc phải giải trình trước bằng tiếng Việt gồm đủ 4 nội dung:
  1. *Sửa phần nào*: Tệp, dòng, hàm hoặc thành phần cụ thể.
  2. *Sửa như thế nào*: Phương án thay đổi chi tiết.
  3. *Tại sao sửa*: Nguyên nhân kỹ thuật/nghiệp vụ.
  4. *Mục đích là gì*: Kết quả kỳ vọng sau sửa.
- **Quy tắc đơn tệp HTML Demo/Wireframe (Single HTML with Tabs & Versioning Rule)**:
  Trong cùng 1 app, chỉ dùng duy nhất 1 file HTML demo. Khi có thêm phương án, không cần sửa đè nếu tốn token — chỉ cần tạo Tab mới ghi Version 2, Version 3... hoặc viết nối tiếp xuống dưới, tuyệt đối không tạo nhiều file lẻ tẻ.

## Stack
- Backend: Flask 3.0, MySQL 8.0, opencv-contrib-python 4.8
- Auth: Flask session + werkzeug password hash
- Realtime: Flask-SocketIO + gevent
- Export: openpyxl untuk Excel, csv built-in untuk CSV
- Deploy: Railway (Procfile + gunicorn + gevent worker)

## Tampilan
- Semua tampilan menggunakan file HTML dari folder templates/stitch/ sebagai referensi
- Konversi ke Jinja2 dengan {% extends 'base.html' %} dan {% block content %}
- Data statis diganti variabel Jinja2: angka hardcode → {{ variabel }}
- Loop data → {% for item in data %}
- Sidebar dan navbar yang identik di semua halaman dipindah ke base.html