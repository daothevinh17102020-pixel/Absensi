"""
Suite kiểm thử tự động toàn bộ API Endpoints cho dự án Absensi.
Tuân thủ tiêu chuẩn /api-test và /test-checklist.
"""
import json
import unittest
from unittest.mock import MagicMock, patch

import app


class ApiEndpointsTestSuite(unittest.TestCase):
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
            sess['is_guest'] = True

    # ---------------------------------------------------------
    # 1. Nhóm Xác Thực (Auth & Session Boundary)
    # ---------------------------------------------------------
    def test_tc_auth_001_unauthorized_api_call(self):
        """TC-AUTH-001: Gọi API khi chưa đăng nhập trả về 401 JSON error"""
        res = self.client.get('/api/search?q=test')
        self.assertEqual(res.status_code, 401)
        self.assertTrue(res.is_json)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'error')

    def test_tc_auth_002_guest_login(self):
        """TC-AUTH-002: Đăng nhập vai trò Khách redirect và cấp session"""
        res = self.client.get('/login/guest')
        self.assertEqual(res.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get('is_guest'))

    def test_tc_auth_003_guest_access_attendance_api(self):
        """TC-AUTH-003: Khách có thể đọc dữ liệu điểm danh hôm nay"""
        self._login_guest()
        with patch.object(app.db, 'get_absensi_hari_ini', return_value=[]):
            res = self.client.get('/api/absensi/hari-ini')
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.is_json)
            data = res.get_json()
            self.assertEqual(data.get('status'), 'ok')

    def test_tc_auth_004_logout_clears_session(self):
        """TC-AUTH-004: Đăng xuất xóa session và redirect về /login"""
        self._login_admin()
        res = self.client.get('/logout')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers.get('Location', ''))
        with self.client.session_transaction() as sess:
            self.assertNotIn('admin_id', sess)
            self.assertFalse(sess.get('is_guest', False))

    # ---------------------------------------------------------
    # 2. Nhóm Điểm Danh Thời Gian Thực (Realtime Attendance)
    # ---------------------------------------------------------
    def test_tc_att_001_get_absensi_hari_ini(self):
        """TC-ATT-001: Lấy danh sách điểm danh hôm nay với quyền Admin"""
        self._login_admin()
        mock_data = [{'id': 1, 'nama': 'DAO VINH', 'status': 'hadir'}]
        with patch.object(app.db, 'get_absensi_hari_ini', return_value=mock_data):
            res = self.client.get('/api/absensi/hari-ini')
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.is_json)
            data = res.get_json()
            self.assertEqual(data.get('status'), 'ok')
            self.assertEqual(len(data.get('data', [])), 1)

    def test_tc_att_002_delete_absensi_success(self):
        """TC-ATT-002: Xóa thành công lượt điểm danh hôm nay"""
        self._login_admin()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'id': 1, 'user_id': 101, 'nama': 'DAO VINH', 'status': 'hadir'}
        mock_conn.cursor.return_value = mock_cursor

        with patch.object(app.db, 'get_connection', return_value=mock_conn):
            res = self.client.post('/api/absensi/hapus/1')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data.get('status'), 'ok')
            self.assertIn('DAO VINH', data.get('pesan', ''))

    def test_tc_att_003_delete_absensi_not_found(self):
        """TC-ATT-003: Xóa lượt điểm danh không tồn tại trả về 404"""
        self._login_admin()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor

        with patch.object(app.db, 'get_connection', return_value=mock_conn):
            res = self.client.post('/api/absensi/hapus/99999')
            self.assertEqual(res.status_code, 404)
            data = res.get_json()
            self.assertEqual(data.get('status'), 'error')

    def test_tc_att_004_manual_attendance_valid(self):
        """TC-ATT-004: Điểm danh thủ công với payload hợp lệ"""
        self._login_admin()
        today = app._get_nama_hari()
        with patch.object(app.db, 'get_user_by_id', return_value={'id': 1, 'nama': 'DAO VINH', 'kelas_id': 1}), \
             patch.object(app.db, 'get_jadwal_by_id', return_value={'id': 1, 'kelas_id': 1, 'nama_kelas': 'K24', 'hari': today}), \
             patch.object(app.db, 'catat_absensi_manual', return_value={'aksi': 'insert', 'status_lama': None}):
            payload = {'user_id': 1, 'jadwal_id': 1, 'status': 'hadir'}
            res = self.client.post('/api/absensi/manual', json=payload)
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data.get('status'), 'ok')

    def test_tc_att_005_manual_attendance_invalid_payload(self):
        """TC-ATT-005: Điểm danh thủ công với payload sai kiểu dữ liệu trả về 400"""
        self._login_admin()
        payload = {'user_id': 'abc', 'jadwal_id': 1, 'status': 'hadir'}
        res = self.client.post('/api/absensi/manual', json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'error')

    # ---------------------------------------------------------
    # 3. Nhóm Camera AI & Sức Khỏe Engine (Vision AI & Camera)
    # ---------------------------------------------------------
    def test_tc_cam_001_face_health(self):
        """TC-CAM-001: Kiểm tra API health check của engine AI"""
        self._login_admin()
        res = self.client.get('/api/face/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('ready'))
        self.assertIn('gallery_ready', data)

    def test_tc_cam_002_camera_toggle_valid(self):
        """TC-CAM-002: Bật/Tắt camera stream từ client với boolean hợp lệ"""
        self._login_admin()
        res = self.client.post('/api/camera/toggle', json={'active': True})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'ok')

    def test_tc_cam_003_camera_toggle_invalid(self):
        """TC-CAM-003: Gửi kiểu dữ liệu không phải boolean bị từ chối 400"""
        self._login_admin()
        res = self.client.post('/api/camera/toggle', json={'active': 'not-a-bool'})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'error')

    # ---------------------------------------------------------
    # 4. Nhóm Học Vụ, Lớp & Lịch Học (Academic & Schedule)
    # ---------------------------------------------------------
    def test_tc_sch_001_jadwal_hari_ini(self):
        """TC-SCH-001: Lấy danh sách ca học hôm nay"""
        self._login_admin()
        with patch.object(app.db, 'get_jadwal_hari', return_value=[]):
            res = self.client.get('/api/jadwal/hari-ini')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data.get('status'), 'ok')

    def test_tc_sch_002_mahasiswa_list(self):
        """TC-SCH-002: Lấy danh sách sinh viên theo bộ lọc lớp"""
        self._login_admin()
        with patch.object(app.db, 'get_semua_user', return_value=[]):
            res = self.client.get('/api/mahasiswa/list?kelas_id=1')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data.get('status'), 'ok')

    def test_tc_sch_003_search_valid(self):
        """TC-SCH-003: Tìm kiếm sinh viên theo từ khóa"""
        self._login_admin()
        mock_students = [{'id': 1, 'nama': 'DAO VINH', 'nim': '24D400056'}]
        with patch.object(app.db, 'cari_mahasiswa', return_value=mock_students), \
             patch.object(app.db, 'cari_jadwal', return_value=[]):
            res = self.client.get('/api/search?q=vinh')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data.get('status'), 'ok')
            self.assertEqual(len(data.get('data', {}).get('mahasiswa', [])), 1)

    def test_tc_sch_004_search_empty_query(self):
        """TC-SCH-004: Tìm kiếm từ khóa rỗng trả về mảng trống an toàn"""
        self._login_admin()
        res = self.client.get('/api/search?q=')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data.get('data'), {'mahasiswa': [], 'jadwal': []})

    # ---------------------------------------------------------
    # 5. Nhóm Đăng Ký Sinh Viên & Huấn Luyện (Enrollment & Training)
    # ---------------------------------------------------------
    def test_tc_enr_001_foto_upload_invalid_missing_fields(self):
        """TC-ENR-001: Tải ảnh thiếu thông tin sinh viên trả về 400"""
        self._login_admin()
        payload = {'nama': '', 'nim': '', 'foto': 'data:image/jpeg;base64,123'}
        res = self.client.post('/api/foto/upload', json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'error')

    def test_tc_trn_001_training_status_not_found(self):
        """TC-TRN-001: Tra cứu build_id không tồn tại hoặc rỗng trả về 404"""
        self._login_admin()
        res = self.client.get('/api/training/status?build_id=invalid-id')
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'error')

    def test_tc_trn_002_training_status_valid(self):
        """TC-TRN-002: Tra cứu trạng thái huấn luyện khi có build_id hợp lệ"""
        self._login_admin()
        state = {'build_id': 'build-123', 'state': 'success', 'count': 24}
        with patch.object(app, '_get_gallery_build_state', return_value=state):
            res = self.client.get('/api/training/status?build_id=build-123')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data.get('status'), 'ok')
            self.assertEqual(data.get('data', {}).get('state'), 'success')

    # ---------------------------------------------------------
    # 6. Nhóm Phân Quyền Khách & Rào Chắn Bảo Mật (Guest RBAC)
    # ---------------------------------------------------------
    def test_tc_guest_001_delete_absensi_forbidden_for_guest(self):
        """TC-GUEST-001: Khách gọi API xóa điểm danh bị từ chối 403 Forbidden"""
        self._login_guest()
        res = self.client.post('/api/absensi/hapus/1')
        self.assertEqual(res.status_code, 403)
        self.assertTrue(res.is_json)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'error')
        self.assertIn('Chỉ Quản trị viên mới được phép', data.get('pesan', ''))

    def test_tc_guest_002_manual_attendance_forbidden_for_guest(self):
        """TC-GUEST-002: Khách gọi API điểm danh thủ công bị từ chối 403 Forbidden"""
        self._login_guest()
        payload = {'user_id': 1, 'jadwal_id': 1, 'status': 'hadir'}
        res = self.client.post('/api/absensi/manual', json=payload)
        self.assertEqual(res.status_code, 403)
        self.assertTrue(res.is_json)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'error')

    def test_tc_guest_003_admin_routes_redirect_guest(self):
        """TC-GUEST-003: Khách gõ URL trang quản trị (/mahasiswa, /kelas...) bị đẩy về Dashboard"""
        self._login_guest()
        for endpoint in ['/mahasiswa', '/mahasiswa/register', '/kelas', '/jadwal', '/laporan']:
            with self.subTest(endpoint=endpoint):
                res = self.client.get(endpoint)
                self.assertEqual(res.status_code, 302, f"Endpoint {endpoint} không redirect khách")
                self.assertEqual(res.headers.get('Location'), '/')

    def test_tc_guest_004_guest_login_endpoint(self):
        """TC-GUEST-004: Endpoint /login/guest thiết lập đúng thông số session và redirect về Dashboard"""
        res = self.client.get('/login/guest')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get('Location'), '/')
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('role'), 'guest')
            self.assertTrue(sess.get('is_guest'))
            self.assertEqual(sess.get('admin_id'), 'guest')
            self.assertEqual(sess.get('username'), 'Khách')

    def test_tc_guest_005_admin_full_access(self):
        """TC-GUEST-005: Quản trị viên truy cập các trang quản trị bình thường (200 OK)"""
        self._login_admin()
        with patch.object(app.db, 'get_semua_user', return_value=[]), \
             patch.object(app.db, 'get_semua_kelas', return_value=[]), \
             patch.object(app._gallery_user_ids, '__call__', return_value=set()):
            res = self.client.get('/mahasiswa')
            self.assertEqual(res.status_code, 200)

    def test_tc_guest_006_guest_can_view_rekap(self):
        """TC-GUEST-006: Khách được phép truy cập /absensi/rekap để xem tổng hợp điểm danh (200 OK)"""
        self._login_guest()
        with patch.object(app.db, 'get_semua_kelas', return_value=[]), \
             patch.object(app.db, 'get_semua_matakuliah', return_value=[]), \
             patch.object(app, '_lay_du_lieu_ma_tran_rekap', return_value=([], {}, [])):
            res = self.client.get('/absensi/rekap')
            self.assertEqual(res.status_code, 200)

    def test_tc_guest_007_guest_forbidden_buoi_hoc_update(self):
        """TC-GUEST-007: Khách bị cấm gọi API cập nhật thông tin buổi học (403 Forbidden)"""
        self._login_guest()
        res = self.client.post('/api/buoi-hoc/update', json={'buoi_so': 5, 'tanggal': '2026-09-06'})
        self.assertEqual(res.status_code, 403)
        self.assertTrue(res.is_json)
        self.assertEqual(res.get_json().get('status'), 'error')


if __name__ == '__main__':
    unittest.main()

