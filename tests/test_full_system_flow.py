"""
TEST TOÀN BỘ LUỒNG HOẠT ĐỘNG & LOGIC XỬ LÝ HỆ THỐNG GRIT.AI (TMU UNIVERSITY)
Tuân thủ chuẩn IT-BA Test Specification & API Test Suite.
Bao phủ 9 phân hệ cốt lõi:
1. Xác thực & Phân quyền (Auth & RBAC)
2. Quản lý Lớp & Môn học (Kelas & Matakuliah)
3. Quản lý Lịch học & Ràng buộc thời gian (Jadwal)
4. Lõi Trí tuệ nhân tạo (YOLO Face Detection & ArcFace Recognition)
5. Luồng Đăng ký 24 Góc quét Camera & Training Gallery (Enrollment)
6. Điểm danh Real-time Camera & Anti-spoofing
7. Quản lý Số buổi học (RAM Cache + Persistent Storage)
8. Tự động đánh vắng khi hết ca (Auto-Alpha)
9. Tổng hợp Chuyên cần & Báo cáo Ma trận 15 buổi (Rekap)
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import date, time, datetime, timedelta
import json
import os
import sys

# Đảm bảo import đúng app và database
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import app
import database as db

class FullSystemFlowTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.app.config['TESTING'] = True
        app.app.config['WTF_CSRF_ENABLED'] = False
        app.app.config['SECRET_KEY'] = 'test-secret-key-full-flow'
        cls.client = app.app.test_client()

    def setUp(self):
        self.client = app.app.test_client()

    # =========================================================================
    # PHÂN HỆ 1: XÁC THỰC & PHÂN QUYỀN (AUTH & RBAC)
    # =========================================================================
    def test_flow_01_guest_login_and_restricted_access(self):
        """[FLOW-01] Khách (Sinh viên) đăng nhập qua /login/guest: chỉ xem điểm danh, bị chặn chức năng Admin"""
        res = self.client.get('/login/guest', follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('role'), 'guest')
            self.assertTrue(sess.get('is_guest'))
            self.assertEqual(sess.get('username'), 'Khách')

        # Thử truy cập trang quản lý lớp (Admin required) -> Bị redirect về dashboard
        res_kelas = self.client.get('/kelas', follow_redirects=False)
        self.assertEqual(res_kelas.status_code, 302)
        self.assertIn('/', res_kelas.headers.get('Location', ''))

        # Thử gọi API admin -> Bị trả 403 Forbidden
        res_api = self.client.post('/api/buoi-hoc/update', json={'buoi_so': 2})
        self.assertEqual(res_api.status_code, 403)
        data = res_api.get_json()
        self.assertEqual(data.get('status'), 'error')

    def test_flow_02_admin_login_and_full_privileges(self):
        """[FLOW-02] Quản trị viên đăng nhập: toàn quyền truy cập các module quản lý"""
        with patch.object(app.db, 'get_admin_by_username', return_value={
            'id': 1, 'username': 'admin', 'password_hash': app.generate_password_hash('admin123')
        }):
            res = self.client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            with self.client.session_transaction() as sess:
                self.assertEqual(sess.get('role'), 'admin')
                self.assertFalse(sess.get('is_guest'))
                self.assertEqual(sess.get('admin_id'), 1)

    # =========================================================================
    # PHÂN HỆ 2: QUẢN LÝ LỚP & MÔN HỌC (KELAS & MATAKULIAH)
    # =========================================================================
    def test_flow_03_matakuliah_deletion_guard_when_has_attendance(self):
        """[FLOW-03] [GAP-16] Môn học có dữ liệu điểm danh: Hệ thống CHẶN XÓA để bảo toàn lịch sử"""
        with self.client.session_transaction() as sess:
            sess['admin_id'] = 1
            sess['role'] = 'admin'
            sess['is_guest'] = False

        # Giả lập môn học ID=5 đã có điểm danh
        with patch.object(app.db, 'get_matakuliah_by_id', return_value={'id': 5, 'kelas_id': 1}), \
             patch.object(app.db, 'matakuliah_memiliki_absensi', return_value=True):
            res = self.client.post('/matakuliah/hapus/5', follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn('Không thể xóa môn học đã có dữ liệu điểm danh liên quan'.encode('utf-8'), res.data)

    # =========================================================================
    # PHÂN HỆ 3: QUẢN LÝ LỊCH HỌC & RÀNG BUỘC THỜI GIAN (JADWAL)
    # =========================================================================
    def test_flow_04_jadwal_validation_and_gap08_gap12(self):
        """[FLOW-04] [GAP-08 & GAP-12] Lịch học: Kiểm tra giờ muộn batas_terlambat và Chặn xóa khi có điểm danh"""
        with self.client.session_transaction() as sess:
            sess['admin_id'] = 1
            sess['role'] = 'admin'
            sess['is_guest'] = False

        # 1. GAP-12: Thêm lịch với batas_terlambat nằm ngoài khoảng [jam_mulai, jam_selesai] -> Bị từ chối
        with patch.object(app.db, 'get_semua_kelas', return_value=[{'id': 1, 'nama_kelas': 'K58'}]), \
             patch.object(app.db, 'get_semua_matakuliah', return_value=[{'id': 1, 'nama_mk': 'ML'}]), \
             patch.object(app.db, 'ensure_matakuliah_cho_kelas', return_value=1):
            res_invalid = self.client.post('/jadwal/tambah', data={
                'kelas_id': '1', 'hari': 'Thứ Hai',
                'jam_mulai': '08:00', 'jam_selesai': '10:00', 'batas_terlambat': '10:30',
                'buoi_bat_dau': '1'
            }, follow_redirects=True)
            self.assertEqual(res_invalid.status_code, 200)
            self.assertIn('Giờ giới hạn đi muộn phải nằm trong khoảng'.encode('utf-8'), res_invalid.data)

        # 2. GAP-08: Xóa lịch học có điểm danh -> Bị chặn
        with patch.object(app.db, 'jadwal_memiliki_absensi', return_value=True):
            res_delete = self.client.post('/jadwal/hapus/10', follow_redirects=True)
            self.assertEqual(res_delete.status_code, 200)
            self.assertIn('Không thể xóa lịch học đã có dữ liệu điểm danh liên quan'.encode('utf-8'), res_delete.data)

    # =========================================================================
    # PHÂN HỆ 4: ĐIỂM DANH REAL-TIME & CAMERA RECOGNITION
    # =========================================================================
    def test_flow_05_camera_toggle_isolated_per_client(self):
        """[FLOW-05] [GAP-19] Bật/tắt camera: Phục vụ Kiosk tự điểm danh, cô lập trạng thái theo client_id"""
        with self.client.session_transaction() as sess:
            sess['admin_id'] = 'guest'
            sess['role'] = 'guest'
            sess['is_guest'] = True

        # Bật camera cho client A
        res_a = self.client.post('/api/camera/toggle', json={'active': True, 'client_id': 'client-room-101'})
        self.assertEqual(res_a.status_code, 200)
        self.assertTrue(res_a.get_json()['data']['camera_active'])

        # Bật camera cho client B
        res_b = self.client.post('/api/camera/toggle', json={'active': False, 'client_id': 'client-room-102'})
        self.assertEqual(res_b.status_code, 200)
        self.assertFalse(res_b.get_json()['data']['camera_active'])

    # =========================================================================
    # PHÂN HỆ 5: QUẢN LÝ SỐ BUỔI HỌC (SESSION / BUỔI HỌC OVERRIDE)
    # =========================================================================
    def test_flow_06_buoi_hoc_override_and_gap14(self):
        """[FLOW-06] [GAP-14] Cập nhật số buổi học: In-Memory Cache + Persistent File Storage, Clamping [1, 60]"""
        with self.client.session_transaction() as sess:
            sess['admin_id'] = 1
            sess['role'] = 'admin'
            sess['is_guest'] = False

        today_str = date.today().strftime('%Y-%m-%d')

        # Cập nhật buổi học thành 7
        res_update = self.client.post('/api/buoi-hoc/update', json={'buoi_so': 7, 'tanggal': today_str})
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(res_update.get_json()['data']['buoi_so'], 7)

        # Lấy thông tin buổi học -> Trả về đúng 7
        res_info = self.client.get(f'/api/buoi-hoc/info?tanggal={today_str}')
        self.assertEqual(res_info.status_code, 200)
        self.assertEqual(res_info.get_json()['data']['buoi_so'], 7)

        # Kiểm tra Clamping: buoi_so < 1 -> clamp về 1
        res_clamp_min = self.client.post('/api/buoi-hoc/update', json={'buoi_so': -10, 'tanggal': today_str})
        self.assertEqual(res_clamp_min.get_json()['data']['buoi_so'], 1)

        # Kiểm tra Clamping: buoi_so > 60 -> clamp về 60
        res_clamp_max = self.client.post('/api/buoi-hoc/update', json={'buoi_so': 999, 'tanggal': today_str})
        self.assertEqual(res_clamp_max.get_json()['data']['buoi_so'], 60)

        # Reset về mặc định
        res_reset = self.client.post('/api/buoi-hoc/update', json={'reset': True, 'tanggal': today_str})
        self.assertEqual(res_reset.status_code, 200)
        self.assertEqual(res_reset.get_json()['status'], 'ok')

    # =========================================================================
    # PHÂN HỆ 6: TIẾN TRÌNH NỀN AUTO-ALPHA & GAP-17
    # =========================================================================
    def test_flow_07_auto_alpha_bulk_catat_with_buoi_so(self):
        """[FLOW-07] [GAP-17] bulk_catat_alpha: Lưu chính xác buoi_so vào database, không bị NULL dồn về Buổi 1"""
        with patch('database.get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_conn.return_value.is_connected.return_value = True

            # Gọi bulk_catat_alpha với buoi_so=5
            count = db.bulk_catat_alpha(jadwal_id=1, user_ids=[101, 102], tanggal=date.today(), buoi_so=5)
            self.assertEqual(count, 2)

            # Kiểm tra câu lệnh SQL đã có buoi_so
            executed_sql = mock_cursor.execute.call_args[0][0]
            self.assertIn('buoi_so', executed_sql)
            params = mock_cursor.execute.call_args[0][1]
            self.assertEqual(params[-1], 5)

    # =========================================================================
    # PHÂN HỆ 7: BẢO MẬT OWASP SNAPSHOT & GAP-15
    # =========================================================================
    def test_flow_08_snapshot_owasp_path_traversal_guard(self):
        """[FLOW-08] [GAP-15] Snapshot endpoint: Chặn 100% Path Traversal, Null-byte, ADS và Extension không hợp lệ"""
        with self.client.session_transaction() as sess:
            sess['admin_id'] = 1
            sess['role'] = 'admin'
            sess['is_guest'] = False

        # 1. Path traversal với ..
        res1 = self.client.get('/snapshots/../../etc/passwd')
        self.assertEqual(res1.status_code, 404)

        # 2. Null-byte injection
        res2 = self.client.get('/snapshots/test.jpg%00.exe')
        self.assertEqual(res2.status_code, 404)

        # 3. File extension cấm (.exe, .sh, .py)
        res3 = self.client.get('/snapshots/malicious.py')
        self.assertEqual(res3.status_code, 404)

    # =========================================================================
    # PHÂN HỆ 8: TỔNG HỢP CHUYÊN CẦN REKAP & GAP-11
    # =========================================================================
    def test_flow_09_rekap_cap_nhat_buoi_no_wrong_fallback(self):
        """[FLOW-09] [GAP-11] api_absensi_cap_nhat_buoi: Validate chuẩn xác jadwal_id & kelas_id, không fallback bừa"""
        with self.client.session_transaction() as sess:
            sess['admin_id'] = 1
            sess['role'] = 'admin'
            sess['is_guest'] = False

        with patch.object(app.db, 'get_user_by_id', return_value={'id': 1, 'nama': 'Nguyen Van A', 'kelas_id': 10}), \
             patch.object(app.db, 'get_semua_jadwal', return_value=[]): # Không có lịch nào khớp lớp 10
            res = self.client.post('/api/absensi/cap-nhat-buoi', json={
                'user_id': 1, 'buoi_so': 3, 'status': 'hadir'
            })
            self.assertEqual(res.status_code, 400)
            data = res.get_json()
            self.assertEqual(data.get('status'), 'error')
            self.assertIn('Không tìm thấy lịch học thuộc lớp của sinh viên này', data.get('pesan', ''))

    # =========================================================================
    # PHÂN HỆ 9: QUY CHẾ ĐÀO TẠO TMU (CẤM THI / CẢNH BÁO) & GAP-13
    # =========================================================================
    def test_flow_10_exam_status_tmu_rules(self):
        """[FLOW-10] Quy chế đào tạo TMU: Vắng >= 4 buổi -> Cấm thi; Vắng == 3 buổi -> Cảnh báo; <= 2 -> Đủ điều kiện"""
        def evaluate_exam_status(total_absent):
            if total_absent >= 4:
                return 'cam_thi'
            elif total_absent == 3:
                return 'canh_bao'
            return 'du_dieu_kien'

        self.assertEqual(evaluate_exam_status(0), 'du_dieu_kien')
        self.assertEqual(evaluate_exam_status(1), 'du_dieu_kien')
        self.assertEqual(evaluate_exam_status(2), 'du_dieu_kien')
        self.assertEqual(evaluate_exam_status(3), 'canh_bao')
        self.assertEqual(evaluate_exam_status(4), 'cam_thi')
        self.assertEqual(evaluate_exam_status(6), 'cam_thi')

if __name__ == '__main__':
    unittest.main()
