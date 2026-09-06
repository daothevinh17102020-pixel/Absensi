"""
Runner kiểm tra thực tế Part II (Test Checklist) và Part III (API Checklist)
trong FULL_GAP_TEST_API_CHECKLIST.md.
Kiểm tra các hành vi thực tế của mã nguồn app.py và database.py.
"""
import unittest
from unittest.mock import MagicMock, patch
import app
import database as db

class ChecklistEmpiricalTestSuite(unittest.TestCase):
    def setUp(self):
        self.app = app.app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def _login_admin(self):
        with self.client.session_transaction() as sess:
            sess['admin_id'] = 1
            sess['username'] = 'admin'
            sess['role'] = 'admin'
            sess['is_guest'] = False

    def _login_guest(self):
        with self.client.session_transaction() as sess:
            sess['admin_id'] = 'guest'
            sess['username'] = 'Tài khoản Khách'
            sess['role'] = 'guest'
            sess['is_guest'] = True

    # -------------------------------------------------------------
    # 1. GAP-01 / CHK-CLS-012 / ACL Item 11: Tạo lớp trùng tên + khóa
    # -------------------------------------------------------------
    def test_gap01_kelas_tambah_duplicate_check(self):
        """GAP-01: app.py có gọi db.kelas_sudah_ada trước khi db.tambah_kelas không?"""
        self._login_admin()
        with patch.object(app.db, 'kelas_sudah_ada', return_value=True) as mock_check, \
             patch.object(app.db, 'tambah_kelas', return_value=2) as mock_add, \
             patch.object(app.db, 'ensure_matakuliah_cho_kelas'):
            res = self.client.post('/kelas/tambah', data={'nama_kelas': 'ML-01', 'angkatan': '2026'})
            # Nếu có check trùng, mock_check phải được gọi và KHÔNG được gọi mock_add
            has_called_check = mock_check.called
            # Kết quả thực tế:
            if not has_called_check and mock_add.called:
                print("\n[EMPIRICAL-RESULT] GAP-01 BUG CONFIRMED: kelas_tambah KHÔNG gọi db.kelas_sudah_ada, vẫn cho thêm lớp trùng!")
            self.assertTrue(has_called_check, "BUG GAP-01: kelas_tambah không kiểm tra kelas_sudah_ada")

    # -------------------------------------------------------------
    # 2. GAP-06 / CHK-CLS-013 / ACL Item 12: Sửa lớp trùng tên + khóa
    # -------------------------------------------------------------
    def test_gap06_kelas_edit_duplicate_check(self):
        """GAP-06: app.py có gọi db.kelas_sudah_ada(exclude_id) khi sửa lớp không?"""
        self._login_admin()
        with patch.object(app.db, 'get_kelas_by_id', return_value={'id': 1, 'nama_kelas': 'ML-01', 'angkatan': '2026'}), \
             patch.object(app.db, 'kelas_sudah_ada', return_value=True) as mock_check, \
             patch.object(app.db, 'update_kelas', return_value=True) as mock_update, \
             patch.object(app.db, 'sync_matakuliah_ten_lop'):
            res = self.client.post('/kelas/edit/1', data={'nama_kelas': 'ML-02', 'angkatan': '2026'})
            has_called_check = mock_check.called
            if not has_called_check and mock_update.called:
                print("\n[EMPIRICAL-RESULT] GAP-06 BUG CONFIRMED: kelas_edit KHÔNG gọi db.kelas_sudah_ada, cho phép sửa trùng với lớp khác!")
            self.assertTrue(has_called_check, "BUG GAP-06: kelas_edit không kiểm tra kelas_sudah_ada")

    # -------------------------------------------------------------
    # 3. GAP-02 / CHK-CLS-014 / ACL Item 13: Xóa lớp có sinh viên
    # -------------------------------------------------------------
    def test_gap02_kelas_hapus_student_check(self):
        """GAP-02: app.py có kiểm tra sinh viên trong lớp (hitung_mahasiswa_per_kelas) trước khi xóa không?"""
        self._login_admin()
        with patch.object(app.db, 'hitung_mahasiswa_per_kelas', return_value=5) as mock_count, \
             patch.object(app.db, 'hapus_kelas', return_value=True) as mock_del:
            res = self.client.post('/kelas/hapus/1')
            has_called_count = mock_count.called
            if not has_called_count and mock_del.called:
                print("\n[EMPIRICAL-RESULT] GAP-02 BUG CONFIRMED: kelas_hapus KHÔNG kiểm tra số SV trước khi xóa, gọi thẳng hapus_kelas!")
            self.assertTrue(has_called_count, "BUG GAP-02: kelas_hapus không kiểm tra số lượng sinh viên trước khi xóa")

    # -------------------------------------------------------------
    # 4. GAP-12 / CHK-SCH-011 / ACL Item 19: batas_terlambat ngoài khoảng
    # -------------------------------------------------------------
    def test_gap12_jadwal_batas_terlambat_validation(self):
        """GAP-12: app.py có validate batas_terlambat nằm trong [jam_mulai, jam_selesai] không?"""
        self._login_admin()
        with patch.object(app.db, 'ensure_matakuliah_cho_kelas', return_value=1), \
             patch.object(app.db, 'tambah_jadwal', return_value=1) as mock_add:
            # batas_terlambat = 23:59 cho ca học 07:00 - 11:30
            res = self.client.post('/jadwal/tambah', data={
                'kelas_id': 1,
                'hari': 'Thứ Hai',
                'jam_mulai': '07:00',
                'jam_selesai': '11:30',
                'batas_terlambat': '23:59'
            })
            # Nếu không validate, tambah_jadwal vẫn được gọi!
            if mock_add.called:
                print("\n[EMPIRICAL-RESULT] GAP-12 BUG CONFIRMED: batas_terlambat ngoài khung giờ (23:59 vs 07:00-11:30) vẫn được thêm thành công!")
            self.assertFalse(mock_add.called, "BUG GAP-12: batas_terlambat ngoài khoảng [jam_mulai, jam_selesai] không bị chặn")

    # -------------------------------------------------------------
    # 5. GAP-07 / CHK-SCH-012 / ACL Item 18: Overlap lịch học cùng lớp
    # -------------------------------------------------------------
    def test_gap07_jadwal_overlap_check(self):
        """GAP-07: app.py có kiểm tra trùng khung giờ cho cùng lớp/thứ không?"""
        self._login_admin()
        with patch.object(app.db, 'ensure_matakuliah_cho_kelas', return_value=1), \
             patch.object(app.db, 'tambah_jadwal', return_value=1) as mock_add:
            # Giả định đã có lịch Thứ Hai 07:00 - 11:30, thêm tiếp ca trùng 08:00 - 10:00
            res = self.client.post('/jadwal/tambah', data={
                'kelas_id': 1,
                'hari': 'Thứ Hai',
                'jam_mulai': '08:00',
                'jam_selesai': '10:00'
            })
            # Kiểm tra xem code có cơ chế check overlap nào không
            # Trong app.py không hề có hàm check overlap
            import inspect
            src = inspect.getsource(app.jadwal_tambah)
            has_overlap_logic = 'overlap' in src.lower() or 'trung' in src.lower() or 'kiem_tra_trung' in src.lower()
            if not has_overlap_logic:
                print("\n[EMPIRICAL-RESULT] GAP-07 BUG CONFIRMED: jadwal_tambah hoàn toàn không có logic kiểm tra overlap lịch học!")
            self.assertTrue(has_overlap_logic, "BUG GAP-07: jadwal_tambah thiếu logic kiểm tra overlap lịch học")

    # -------------------------------------------------------------
    # 6. GAP-08 / CHK-SCH-014 / ACL Item 20: Xóa lịch học có điểm danh
    # -------------------------------------------------------------
    def test_gap08_jadwal_hapus_has_attendance(self):
        """GAP-08: app.py có kiểm tra dữ liệu điểm danh trước khi xóa lịch không?"""
        self._login_admin()
        import inspect
        src = inspect.getsource(app.jadwal_hapus)
        has_absensi_guard = 'absensi' in src.lower()
        if not has_absensi_guard:
            print("\n[EMPIRICAL-RESULT] GAP-08 BUG CONFIRMED: jadwal_hapus gọi thẳng db.hapus_jadwal mà không kiểm tra dữ liệu điểm danh!")
        self.assertTrue(has_absensi_guard, "BUG GAP-08: jadwal_hapus không kiểm tra lịch sử điểm danh trước khi xóa")

    # -------------------------------------------------------------
    # 7. GAP-10 / CHK-STU-022 / ACL Item 24: Đổi lớp không rebuild gallery
    # -------------------------------------------------------------
    def test_gap10_mahasiswa_edit_rebuild_gallery(self):
        """GAP-10: Sửa thông tin SV có gọi _start_gallery_rebuild_background khi đổi lớp không?"""
        self._login_admin()
        with patch.object(app.db, 'get_user_by_id', return_value={'id': 1, 'nama': 'SV A', 'nim': '001', 'kelas_id': 1}), \
             patch.object(app.db, 'update_user', return_value=True), \
             patch.object(app, '_start_gallery_rebuild_background') as mock_rebuild:
            res = self.client.post('/mahasiswa/edit/1', data={'nama': 'SV A', 'nim': '001', 'kelas_id': 2})
            if not mock_rebuild.called:
                print("\n[EMPIRICAL-RESULT] GAP-10 BUG CONFIRMED: mahasiswa_edit đổi lớp nhưng KHÔNG kích hoạt rebuild gallery!")
            self.assertTrue(mock_rebuild.called, "BUG GAP-10: đổi lớp không kích hoạt rebuild gallery")

    # -------------------------------------------------------------
    # 8. GAP-11 / CHK-REK-014 / ACL Item 48: Fallback sai lịch trong cap_nhat_buoi
    # -------------------------------------------------------------
    def test_gap11_cap_nhat_buoi_wrong_fallback(self):
        """GAP-11: cap_nhat_buoi nếu SV thuộc lớp không có lịch, có lấy bừa jadwal[0] của lớp khác không?"""
        self._login_admin()
        user = {'id': 101, 'nama': 'SV Test', 'kelas_id': 99} # Lớp 99 không có lịch
        schedules = [{'id': 7, 'kelas_id': 1, 'nama_kelas': 'Lớp Khác'}]
        with patch.object(app.db, 'get_user_by_id', return_value=user), \
             patch.object(app.db, 'get_semua_jadwal', return_value=schedules), \
             patch.object(app.db, 'cap_nhat_absensi_buoi', return_value={'id': 1}) as mock_update:
            res = self.client.post('/api/absensi/cap-nhat-buoi', json={'user_id': 101, 'buoi_so': 2, 'status': 'hadir'})
            # Nếu mock_update được gọi với jadwal_id = 7 (của lớp khác) -> BUG!
            if mock_update.called:
                args = mock_update.call_args[0]
                if args[1] == 7:
                    print("\n[EMPIRICAL-RESULT] GAP-11 BUG CONFIRMED: cap_nhat_buoi tự ý gán jadwal_id=7 của LỚP KHÁC cho SV lớp 99!")
            self.assertNotEqual(res.status_code, 200, "BUG GAP-11: không chặn trường hợp SV lớp không có lịch, lại gán lịch của lớp khác")

    # -------------------------------------------------------------
    # 9. GAP-03 / CHK-ALP-010: Cả lớp không ai điểm danh vẫn đánh vắng
    # -------------------------------------------------------------
    def test_gap03_auto_alpha_missing_guard(self):
        """GAP-03: _auto_alpha_checker có gọi db.ada_mahasiswa_hadir_jadwal trước khi bulk_catat_alpha không?"""
        import inspect
        src = inspect.getsource(app._auto_alpha_checker)
        has_guard = 'ada_mahasiswa_hadir_jadwal' in src
        if not has_guard:
            print("\n[EMPIRICAL-RESULT] GAP-03 BUG CONFIRMED: _auto_alpha_checker KHÔNG kiểm tra ada_mahasiswa_hadir_jadwal, đánh vắng cả lớp khi nghỉ lễ!")
        self.assertTrue(has_guard, "BUG GAP-03: _auto_alpha_checker không kiểm tra ada_mahasiswa_hadir_jadwal")

    # -------------------------------------------------------------
    # 10. GAP-17 / CHK-ALP-011: bulk_catat_alpha không set buoi_so
    # -------------------------------------------------------------
    def test_gap17_bulk_catat_alpha_missing_buoi_so(self):
        """GAP-17: db.bulk_catat_alpha có trường buoi_so trong câu lệnh INSERT không?"""
        import inspect
        src = inspect.getsource(db.bulk_catat_alpha)
        has_buoi_so = 'buoi_so' in src
        if not has_buoi_so:
            print("\n[EMPIRICAL-RESULT] GAP-17 BUG CONFIRMED: bulk_catat_alpha câu lệnh INSERT thiếu cột buoi_so!")
        self.assertTrue(has_buoi_so, "BUG GAP-17: bulk_catat_alpha không lưu buoi_so")

    # -------------------------------------------------------------
    # 11. GAP-16 / CHK-MK-012 / ACL Item 15: Xóa môn học có điểm danh
    # -------------------------------------------------------------
    def test_gap16_matakuliah_hapus_unused_guard(self):
        """GAP-16: matakuliah_hapus có gọi matakuliah_memiliki_absensi không?"""
        import inspect
        src = inspect.getsource(app.matakuliah_hapus)
        has_guard = 'matakuliah_memiliki_absensi' in src
        if not has_guard:
            print("\n[EMPIRICAL-RESULT] GAP-16 BUG CONFIRMED: matakuliah_hapus không gọi matakuliah_memiliki_absensi dù hàm đã có sẵn trong database.py!")
        self.assertTrue(has_guard, "BUG GAP-16: matakuliah_hapus không kiểm tra matakuliah_memiliki_absensi")

    # -------------------------------------------------------------
    # 12. GAP-04 / CHK-AUTH-030 / ACL Item 6: Session role sau khi register admin
    # -------------------------------------------------------------
    def test_gap04_register_admin_session_completeness(self):
        """GAP-04: Sau khi đăng ký admin đầu tiên, session có đủ role='admin' và is_guest=False không?"""
        with patch.object(app.db, 'tambah_admin', return_value=1):
            res = self.client.post('/register', data={
                'username': 'newadmin',
                'password': 'password123',
                'confirm': 'password123'
            })
            with self.client.session_transaction() as sess:
                role = sess.get('role')
                is_guest = sess.get('is_guest')
                if role != 'admin' or is_guest is not False:
                    print(f"\n[EMPIRICAL-RESULT] GAP-04 BUG CONFIRMED: Register admin chỉ set admin_id, thiếu role={role}, is_guest={is_guest}!")
                self.assertEqual(role, 'admin', "BUG GAP-04: session thiếu role='admin'")
                self.assertFalse(is_guest, "BUG GAP-04: session thiếu is_guest=False")

    # -------------------------------------------------------------
    # 13. GAP-19 / CHK-AUTH-027 / ACL Item 54: Guest camera toggle permissions
    # -------------------------------------------------------------
    def test_gap19_guest_camera_toggle_security(self):
        """GAP-19: Khách (Guest) có được phép gọi API camera toggle và absensi proses không?"""
        self._login_guest()
        # Test toggle camera
        res = self.client.post('/api/camera/toggle', json={'active': True})
        # Hiện tại app.py dùng @login_required nên guest được qua (200)
        if res.status_code == 200:
            print(f"\n[EMPIRICAL-RESULT] GAP-19 SECURITY BEHAVIOR: Guest được phép gọi /api/camera/toggle (status=200). Cần phân loại: Self-service vs Security Risk.")

    # -------------------------------------------------------------
    # 14. GAP-15 / CHK-AUTH-033 / ACL Item 60: Snapshot path traversal
    # -------------------------------------------------------------
    def test_gap15_snapshot_path_traversal(self):
        """GAP-15: /snapshots/<path:filename> có chặn path traversal không?"""
        self._login_admin()
        res = self.client.get('/snapshots/../../etc/passwd')
        # Flask send_from_directory tự động chặn 404
        self.assertEqual(res.status_code, 404)
        print(f"\n[EMPIRICAL-RESULT] GAP-15 VERIFIED: Flask send_from_directory đã chặn an toàn path traversal (HTTP 404).")

    # -------------------------------------------------------------
    # 15. CHK-BH-010, 011: Buổi học update validation
    # -------------------------------------------------------------
    def test_buoi_hoc_clamping(self):
        """CHK-BH-010 & 011: buoi_so < 1 clamp to 1, buoi_so > 60 clamp to 60"""
        self._login_admin()
        res1 = self.client.post('/api/buoi-hoc/update', json={'buoi_so': -5, 'tanggal': '2026-09-09'})
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertEqual(data1['data']['buoi_so'], 1)

        res2 = self.client.post('/api/buoi-hoc/update', json={'buoi_so': 999, 'tanggal': '2026-09-09'})
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertEqual(data2['data']['buoi_so'], 60)
        print(f"\n[EMPIRICAL-RESULT] CHK-BH-010/011 PASS: buoi_so clamping hoạt động chính xác (1 đến 60).")

    # -------------------------------------------------------------
    # 16. CHK-REK-020, 021, 022: Business rule cấm thi / cảnh báo
    # -------------------------------------------------------------
    def test_rekap_exam_status_rules(self):
        """CHK-REK-020/021/022: >=4 vắng -> cấm thi, 3 vắng -> cảnh báo, <=2 -> đủ điều kiện"""
        # Logic tính trong app.py:
        # if so_buoi_vang >= 4: 'cam_thi'
        # elif so_buoi_vang == 3: 'canh_bao'
        # else: 'du_dieu_kien'
        self.assertEqual(app._danh_gia_dieu_kien_thi(4)['status'], 'cam_thi')
        self.assertEqual(app._danh_gia_dieu_kien_thi(5)['status'], 'cam_thi')
        self.assertEqual(app._danh_gia_dieu_kien_thi(3)['status'], 'canh_bao')
        self.assertEqual(app._danh_gia_dieu_kien_thi(2)['status'], 'du_dieu_kien')
        self.assertEqual(app._danh_gia_dieu_kien_thi(0)['status'], 'du_dieu_kien')
        print(f"\n[EMPIRICAL-RESULT] CHK-REK-020/021/022 PASS: Quy tắc cấm thi (>=4), cảnh báo (==3), đủ điều kiện (<=2) hoạt động chuẩn xác.")

if __name__ == '__main__':
    unittest.main()
