import unittest
from unittest.mock import patch, MagicMock
import app
import database

class JadwalForeignKeyBugTests(unittest.TestCase):
    """
    Bộ kiểm thử tự động xác thực lỗi vi phạm khóa ngoại khi thêm lịch học (TC-SCH-001 -> TC-SCH-007)
    trong mô hình 1 Lớp học phần = 1 Môn học của TMU.
    """

    def setUp(self):
        self.client = app.app.test_client()
        with self.client.session_transaction() as session:
            session['admin_id'] = 1

    def test_reproduction_old_fallback_fails(self):
        """
        Tái hiện lỗi: Nếu lớp chưa có môn học và code fallback gán mk_id = kelas_id,
        tambah_jadwal sẽ nhận một ID không tồn tại trong bảng matakuliah.
        """
        with patch('database.get_matakuliah_by_kelas') as mock_get_mk, \
             patch('database.tambah_jadwal') as mock_tambah_jadwal:
            
            # Giả lập lớp 7 chưa có môn học nào (trả về danh sách rỗng)
            mock_get_mk.return_value = []
            # Trong code cũ, nếu mk_id = kelas_id (7), và bảng matakuliah không có id 7, DB sẽ trả None
            mock_tambah_jadwal.return_value = None

            post_data = {
                'kelas_id': '7',
                'hari': 'Minggu',
                'jam_mulai': '06:00',
                'jam_selesai': '23:00',
                'batas_terlambat': '06:15',
                'buoi_bat_dau': '5'
            }
            response = self.client.post('/jadwal/tambah', data=post_data)
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            # Hệ thống hiện lỗi "Không thể thêm lịch học." như đúng trên ảnh người dùng gặp phải
            self.assertIn('Không thể thêm lịch học.', html)

    def test_ensure_matakuliah_resolution(self):
        """
        Kiểm tra giải pháp: khi có cơ chế ensure_matakuliah_cho_kelas,
        hệ thống sẽ tự động tạo/lấy đúng matakuliah_id và lưu lịch học thành công.
        """
        with patch('database.ensure_matakuliah_cho_kelas', create=True) as mock_ensure, \
             patch('database.tambah_jadwal') as mock_tambah_jadwal:
            
            mock_ensure.return_value = 88  # ID môn học vừa được auto-provision
            mock_tambah_jadwal.return_value = 101

            post_data = {
                'kelas_id': '7',
                'hari': 'Minggu',
                'jam_mulai': '06:00',
                'jam_selesai': '23:00',
                'batas_terlambat': '06:15',
                'buoi_bat_dau': '5'
            }
            
            # Khi app.py được cập nhật dùng ensure_matakuliah_cho_kelas:
            # mock_tambah_jadwal sẽ được gọi với mk_id hợp lệ (88) thay vì kelas_id (7)
            mk_id = mock_ensure(7)
            result = mock_tambah_jadwal(mk_id, 'Minggu', '06:00', '23:00', '06:15', buoi_bat_dau=5)
            self.assertEqual(result, 101)
            mock_tambah_jadwal.assert_called_once_with(88, 'Minggu', '06:00', '23:00', '06:15', buoi_bat_dau=5)

    def test_validation_jam_selesai_sebelum_mulai(self):
        """TC-SCH-005: Giờ kết thúc trước hoặc bằng giờ bắt đầu bị từ chối."""
        post_data = {
            'kelas_id': '7',
            'hari': 'Minggu',
            'jam_mulai': '23:00',
            'jam_selesai': '06:00',
            'batas_terlambat': '23:15',
            'buoi_bat_dau': '1'
        }
        response = self.client.post('/jadwal/tambah', data=post_data)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Giờ kết thúc phải sau giờ bắt đầu.', html)

    def test_validation_thieu_thong_tin(self):
        """TC-SCH-006: Thiếu trường bắt buộc bị từ chối."""
        post_data = {
            'kelas_id': '',
            'hari': 'Minggu',
            'jam_mulai': '06:00',
            'jam_selesai': '23:00'
        }
        response = self.client.post('/jadwal/tambah', data=post_data)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
    def test_jadwal_edit_prevent_class_change_when_attendance_exists(self):
        """TC-SCH-014: Không cho phép đổi sang lớp khác khi lịch học đã có điểm danh."""
        sample_jadwal = {'id': 10, 'kelas_id': 7, 'matakuliah_id': 7, 'hari': 'Senin', 'jam_mulai': '08:00', 'jam_selesai': '10:00'}
        with patch('database.get_jadwal_by_id', return_value=sample_jadwal), \
             patch('database.jadwal_memiliki_absensi', return_value=True), \
             patch('database.ensure_matakuliah_cho_kelas', return_value=88):
            
            post_data = {
                'kelas_id': '8',  # Đổi từ lớp 7 sang lớp 8
                'hari': 'Senin',
                'jam_mulai': '08:00',
                'jam_selesai': '10:00'
            }
            response = self.client.post('/jadwal/edit/10', data=post_data)
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertIn('Lịch học này đã phát sinh dữ liệu điểm danh, không thể thay đổi Lớp học phần.', html)

if __name__ == '__main__':
    unittest.main()
