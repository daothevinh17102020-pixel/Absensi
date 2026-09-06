import unittest
from unittest.mock import patch, MagicMock
import app
import database

class ScheduleEditTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        with self.client.session_transaction() as session:
            session['admin_id'] = 1

        self.sample_jadwal = {
            'id': 10,
            'matakuliah_id': 2,
            'nama_mk': 'Pemrograman Web',
            'kode_mk': 'MK002',
            'kelas_id': 1,
            'nama_kelas': 'IK-1',
            'hari': 'Senin',
            'jam_mulai': '08:00:00',
            'jam_selesai': '10:30:00',
            'batas_terlambat': '08:15:00'
        }
        self.sample_kelas = [{'id': 1, 'nama_kelas': 'IK-1', 'angkatan': 2022}]
        self.sample_mk = [{'id': 2, 'nama_mk': 'Pemrograman Web', 'kode_mk': 'MK002', 'kelas_id': 1, 'sks': 3}]

    @patch('database.get_semua_jadwal')
    def test_jadwal_index_renders_edit_link(self, mock_get_semua):
        mock_get_semua.return_value = [self.sample_jadwal]
        response = self.client.get('/jadwal')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('/jadwal/edit/10', html)
        self.assertNotIn('title="Chức năng sửa chưa có route backend"', html)

    @patch('database.get_semua_matakuliah')
    @patch('database.get_semua_kelas')
    def test_jadwal_tambah_get_renders_form(self, mock_kelas, mock_mk):
        mock_kelas.return_value = self.sample_kelas
        mock_mk.return_value = self.sample_mk
        response = self.client.get('/jadwal/tambah')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Thêm lịch học mới', html)
        self.assertIn('Thêm lịch học', html)

    @patch('database.get_semua_matakuliah')
    @patch('database.get_semua_kelas')
    @patch('database.get_jadwal_by_id')
    def test_jadwal_edit_get_valid_id(self, mock_get_jadwal, mock_kelas, mock_mk):
        mock_get_jadwal.return_value = self.sample_jadwal
        mock_kelas.return_value = self.sample_kelas
        mock_mk.return_value = self.sample_mk

        response = self.client.get('/jadwal/edit/10')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Sửa lịch học', html)
        self.assertIn('Cập nhật lịch học', html)
        self.assertIn('08:00', html)
        self.assertIn('10:30', html)
        self.assertIn('08:15', html)
        self.assertIn('name="batas_terlambat"', html)
        self.assertNotIn('Hạn đi muộn được tính tự động: giờ bắt đầu + 15 phút.', html)
        self.assertNotIn('Trước tiên hãy chọn lớp, sau đó chọn môn học của lớp đó.', html)

    @patch('database.update_jadwal')
    @patch('database.get_jadwal_by_id')
    def test_jadwal_edit_post_custom_batas_terlambat(self, mock_get_jadwal, mock_update_jadwal):
        mock_get_jadwal.return_value = self.sample_jadwal
        mock_update_jadwal.return_value = True

        post_data = {
            'kelas_id': '1',
            'matakuliah_id': '2',
            'hari': 'Selasa',
            'jam_mulai': '08:00',
            'jam_selesai': '10:30',
            'batas_terlambat': '08:20'
        }
        response = self.client.post('/jadwal/edit/10', data=post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        mock_update_jadwal.assert_called_once_with(10, 2, 'Selasa', '08:00', '10:30', '08:20')
        html = response.get_data(as_text=True)
        self.assertIn('Cập nhật lịch học thành công!', html)

    @patch('database.get_jadwal_by_id')
    def test_jadwal_edit_get_nonexistent_id_redirects(self, mock_get_jadwal):
        mock_get_jadwal.return_value = None
        response = self.client.get('/jadwal/edit/99999', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Lịch học không tồn tại.', html)

    @patch('database.update_jadwal')
    @patch('database.get_jadwal_by_id')
    def test_jadwal_edit_post_success(self, mock_get_jadwal, mock_update_jadwal):
        mock_get_jadwal.return_value = self.sample_jadwal
        mock_update_jadwal.return_value = True

        post_data = {
            'kelas_id': '1',
            'matakuliah_id': '2',
            'hari': 'Selasa',
            'jam_mulai': '09:00',
            'jam_selesai': '11:30'
        }
        response = self.client.post('/jadwal/edit/10', data=post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        mock_update_jadwal.assert_called_once_with(10, 2, 'Selasa', '09:00', '11:30')
        html = response.get_data(as_text=True)
        self.assertIn('Cập nhật lịch học thành công!', html)

    @patch('database.get_semua_matakuliah')
    @patch('database.get_semua_kelas')
    @patch('database.update_jadwal')
    @patch('database.get_jadwal_by_id')
    def test_jadwal_edit_post_validation_error_missing_field(self, mock_get_jadwal, mock_update, mock_kelas, mock_mk):
        mock_get_jadwal.return_value = self.sample_jadwal
        mock_kelas.return_value = self.sample_kelas
        mock_mk.return_value = self.sample_mk

        post_data = {
            'kelas_id': '1',
            'matakuliah_id': '2',
            'hari': '',
            'jam_mulai': '09:00',
            'jam_selesai': '11:30'
        }
        response = self.client.post('/jadwal/edit/10', data=post_data)
        self.assertEqual(response.status_code, 200)
        mock_update.assert_not_called()
        html = response.get_data(as_text=True)
        self.assertIn('Vui lòng nhập đầy đủ thông tin.', html)

    @patch('database.get_semua_matakuliah')
    @patch('database.get_semua_kelas')
    @patch('database.update_jadwal')
    @patch('database.get_jadwal_by_id')
    def test_jadwal_edit_post_validation_error_invalid_time_range(self, mock_get_jadwal, mock_update, mock_kelas, mock_mk):
        mock_get_jadwal.return_value = self.sample_jadwal
        mock_kelas.return_value = self.sample_kelas
        mock_mk.return_value = self.sample_mk

        post_data = {
            'kelas_id': '1',
            'matakuliah_id': '2',
            'hari': 'Senin',
            'jam_mulai': '10:00',
            'jam_selesai': '09:00'
        }
        response = self.client.post('/jadwal/edit/10', data=post_data)
        self.assertEqual(response.status_code, 200)
        mock_update.assert_not_called()
        html = response.get_data(as_text=True)
        self.assertIn('Giờ kết thúc phải sau giờ bắt đầu.', html)

    @patch('database.tambah_jadwal')
    def test_jadwal_tambah_post_success(self, mock_tambah_jadwal):
        mock_tambah_jadwal.return_value = 11
        post_data = {
            'kelas_id': '1',
            'matakuliah_id': '2',
            'hari': 'Rabu',
            'jam_mulai': '13:00',
            'jam_selesai': '15:30'
        }
        response = self.client.post('/jadwal/tambah', data=post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        mock_tambah_jadwal.assert_called_once_with(2, 'Rabu', '13:00', '15:30')
        html = response.get_data(as_text=True)
        self.assertIn('Thêm lịch học thành công!', html)

    @patch('database.tambah_jadwal')
    def test_jadwal_tambah_post_with_buoi_bat_dau(self, mock_tambah_jadwal):
        mock_tambah_jadwal.return_value = 12
        post_data = {
            'kelas_id': '1',
            'matakuliah_id': '2',
            'hari': 'Kamis',
            'jam_mulai': '07:00',
            'jam_selesai': '09:30',
            'buoi_bat_dau': '5'
        }
        response = self.client.post('/jadwal/tambah', data=post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        mock_tambah_jadwal.assert_called_once_with(2, 'Kamis', '07:00', '09:30', buoi_bat_dau=5)
        html = response.get_data(as_text=True)
        self.assertIn('Thêm lịch học thành công!', html)

    @patch('database.jadwal_memiliki_absensi')
    @patch('database.hapus_jadwal')
    def test_jadwal_hapus_post_success(self, mock_hapus_jadwal, mock_memiliki_absensi):
        mock_memiliki_absensi.return_value = False
        mock_hapus_jadwal.return_value = True
        response = self.client.post('/jadwal/hapus/10', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        mock_memiliki_absensi.assert_called_once_with(10)
        mock_hapus_jadwal.assert_called_once_with(10)
        html = response.get_data(as_text=True)
        self.assertIn('Xóa lịch học thành công.', html)

    @patch('database.jadwal_memiliki_absensi')
    @patch('database.hapus_jadwal')
    def test_jadwal_hapus_post_blocked_when_has_attendance(self, mock_hapus_jadwal, mock_memiliki_absensi):
        mock_memiliki_absensi.return_value = True
        response = self.client.post('/jadwal/hapus/10', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        mock_memiliki_absensi.assert_called_once_with(10)
        mock_hapus_jadwal.assert_not_called()
        html = response.get_data(as_text=True)
        self.assertIn('Không thể xóa lịch học đã có dữ liệu điểm danh', html)

    @patch('database.get_connection')
    def test_database_update_jadwal_helper(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        result = database.update_jadwal(10, 2, 'Senin', '08:00', '10:00')
        self.assertTrue(result)
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()


    @patch('database.get_semua_matakuliah')
    @patch('database.get_semua_kelas')
    def test_jadwal_form_renders_sunday_option(self, mock_kelas, mock_mk):
        mock_kelas.return_value = self.sample_kelas
        mock_mk.return_value = self.sample_mk
        response = self.client.get('/jadwal/tambah')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('value="Minggu"', html)
        self.assertIn('Chủ Nhật', html)

    @patch('database.get_semua_matakuliah')
    @patch('database.get_semua_kelas')
    @patch('database.get_jadwal_by_id')
    def test_jadwal_edit_renders_sunday_selected(self, mock_get_jadwal, mock_kelas, mock_mk):
        sunday_jadwal = dict(self.sample_jadwal)
        sunday_jadwal['hari'] = 'Minggu'
        mock_get_jadwal.return_value = sunday_jadwal
        mock_kelas.return_value = self.sample_kelas
        mock_mk.return_value = self.sample_mk

        response = self.client.get('/jadwal/edit/10')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('value="Minggu" selected', html)
        self.assertIn('Chủ Nhật', html)

    @patch('database.tambah_jadwal')
    def test_jadwal_tambah_post_sunday_success(self, mock_tambah_jadwal):
        mock_tambah_jadwal.return_value = 99
        post_data = {
            'kelas_id': '1',
            'matakuliah_id': '2',
            'hari': 'Minggu',
            'jam_mulai': '08:00',
            'jam_selesai': '11:00',
        }
        response = self.client.post('/jadwal/tambah', data=post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        mock_tambah_jadwal.assert_called_once_with(2, 'Minggu', '08:00', '11:00')
        html = response.get_data(as_text=True)
        self.assertIn('Thêm lịch học thành công!', html)

    @patch('database.update_jadwal')
    @patch('database.get_jadwal_by_id')
    def test_jadwal_edit_post_sunday_success(self, mock_get_jadwal, mock_update_jadwal):
        mock_get_jadwal.return_value = self.sample_jadwal
        mock_update_jadwal.return_value = True
        post_data = {
            'kelas_id': '1',
            'matakuliah_id': '2',
            'hari': 'Minggu',
            'jam_mulai': '08:30',
            'jam_selesai': '11:30',
            'batas_terlambat': '08:45'
        }
        response = self.client.post('/jadwal/edit/10', data=post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        mock_update_jadwal.assert_called_once_with(10, 2, 'Minggu', '08:30', '11:30', '08:45')
        html = response.get_data(as_text=True)
    @patch('database.get_matakuliah_by_kelas')
    @patch('database.update_jadwal')
    @patch('database.get_jadwal_by_id')
    def test_jadwal_edit_post_with_only_kelas_id(self, mock_get_jadwal, mock_update_jadwal, mock_get_mk_by_kelas):
        mock_get_jadwal.return_value = self.sample_jadwal
        mock_update_jadwal.return_value = True
        mock_get_mk_by_kelas.return_value = [{'id': 2, 'nama_mk': 'Pemrograman Web'}]
        # Giả lập đúng payload gửi từ form HTML (chỉ có kelas_id, không có matakuliah_id)
        post_data = {
            'kelas_id': '1',
            'hari': 'Selasa',
            'jam_mulai': '06:00',
            'jam_selesai': '23:00',
            'batas_terlambat': '06:45',
            'buoi_bat_dau': '1'
        }
        response = self.client.post('/jadwal/edit/10', data=post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        mock_update_jadwal.assert_called_once_with(10, 2, 'Selasa', '06:00', '23:00', '06:45', buoi_bat_dau=1)
        html = response.get_data(as_text=True)
        self.assertIn('Cập nhật lịch học thành công!', html)

    @patch('database.get_matakuliah_by_kelas')
    @patch('database.tambah_jadwal')
    def test_jadwal_tambah_post_with_only_kelas_id(self, mock_tambah_jadwal, mock_get_mk_by_kelas):
        mock_tambah_jadwal.return_value = 100
        mock_get_mk_by_kelas.return_value = [{'id': 5, 'nama_mk': 'Machine Learning'}]
        post_data = {
            'kelas_id': '6',
            'hari': 'Minggu',
            'jam_mulai': '08:00',
            'jam_selesai': '11:00',
            'buoi_bat_dau': '1'
        }
        response = self.client.post('/jadwal/tambah', data=post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        mock_tambah_jadwal.assert_called_once_with(5, 'Minggu', '08:00', '11:00', buoi_bat_dau=1)
        html = response.get_data(as_text=True)
        self.assertIn('Thêm lịch học thành công!', html)


if __name__ == '__main__':
    unittest.main()

