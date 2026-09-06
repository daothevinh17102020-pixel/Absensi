import unittest
from unittest.mock import patch, MagicMock
from datetime import date, time, datetime, timedelta
from zoneinfo import ZoneInfo
import app
import database

class BuoiHocRulesTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        with self.client.session_transaction() as session:
            session['admin_id'] = 1

    # =========================================================================
    # QUY TẮC 1: Không có lịch học nào trong hệ thống -> Trả về RỖNG
    # =========================================================================
    @patch('database.get_connection')
    def test_rule_1_empty_schedule_returns_blank(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.return_value.cursor.return_value = mock_cursor

        info = database.get_thong_tin_buoi_hoc_hom_nay()
        self.assertFalse(info['has_jadwal'])
        self.assertEqual(info['thu'], '')
        self.assertEqual(info['tanggal'], '')
        self.assertEqual(info['lop_hoc_phan'], '')
        self.assertEqual(info['jam_mulai'], '')
        self.assertEqual(info['jam_selesai'], '')
        self.assertEqual(info['buoi_so'], '')

        # Kiểm tra API endpoint /api/buoi-hoc/info khi rỗng
        with patch('database.get_thong_tin_buoi_hoc_hom_nay', return_value=info):
            res = self.client.get('/api/buoi-hoc/info')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()['data']
            self.assertFalse(data['has_jadwal'])
            self.assertEqual(data['lop_hoc_phan'], '')

    # =========================================================================
    # QUY TẮC 2: Có nhiều lịch học -> Tự động lấy ca học GẦN NHẤT
    # =========================================================================
    @patch('database.get_buoi_hoc_hien_tai_cua_lop', return_value=2)
    @patch('database._now_app')
    @patch('database.get_connection')
    def test_rule_2_multiple_schedules_picks_nearest(self, mock_conn, mock_now, mock_buoi):
        # Giả lập thời điểm hiện tại: Thứ Bảy ngày 05/09/2026 10:00
        # Lịch 1: Thứ Hai (Senin) -> Cách 2 ngày (2026-09-07)
        # Lịch 2: Thứ Năm (Kamis) -> Cách 5 ngày (2026-09-10)
        jadwal_mon = {
            'id': 1, 'hari': 'Senin', 'jam_mulai': '07:00:00', 'jam_selesai': '11:30:00',
            'nama_kelas': 'Lớp Thứ Hai', 'nama_mk': 'Môn Thứ Hai', 'kode_mk': 'MK01',
            'kelas_id': 10, 'buoi_bat_dau': 1, 'batas_terlambat': None
        }
        jadwal_thu = {
            'id': 2, 'hari': 'Kamis', 'jam_mulai': '07:00:00', 'jam_selesai': '11:30:00',
            'nama_kelas': 'Lớp Thứ Năm', 'nama_mk': 'Môn Thứ Năm', 'kode_mk': 'MK02',
            'kelas_id': 11, 'buoi_bat_dau': 1, 'batas_terlambat': None
        }
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [jadwal_thu, jadwal_mon]
        mock_conn.return_value.cursor.return_value = mock_cursor

        tz = ZoneInfo("Asia/Jakarta")
        mock_now.return_value = datetime(2026, 9, 5, 10, 0, 0, tzinfo=tz) # Thứ Bảy

        info = database.get_thong_tin_buoi_hoc_hom_nay()
        self.assertTrue(info['has_jadwal'])
        self.assertEqual(info['thu'], 'Thứ Hai')
        self.assertEqual(info['tanggal'], '2026-09-07')
        self.assertEqual(info['nama_kelas'], 'Lớp Thứ Hai')

    # =========================================================================
    # QUY TẮC 3: Lịch học Thứ 4, hôm nay Thứ 7 (đã qua) -> Lấy Thứ 4 tuần sau
    # =========================================================================
    @patch('database.get_buoi_hoc_hien_tai_cua_lop', return_value=5)
    @patch('database._now_app')
    @patch('database.get_connection')
    def test_rule_3_past_weekday_jumps_to_next_week(self, mock_conn, mock_now, mock_buoi):
        jadwal_wed = {
            'id': 16, 'hari': 'Rabu', 'jam_mulai': '06:00:00', 'jam_selesai': '23:00:00',
            'nama_kelas': 'ML - 02', 'nama_mk': 'ML - 02', 'kode_mk': 'ML02_6',
            'kelas_id': 6, 'buoi_bat_dau': 5, 'batas_terlambat': None
        }
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [jadwal_wed]
        mock_conn.return_value.cursor.return_value = mock_cursor

        tz = ZoneInfo("Asia/Jakarta")
        # Giả lập hôm nay là Thứ Bảy 05/09/2026 (Thứ 4 tuần này 02/09 đã qua)
        mock_now.return_value = datetime(2026, 9, 5, 15, 0, 0, tzinfo=tz)

        info = database.get_thong_tin_buoi_hoc_hom_nay()
        self.assertTrue(info['has_jadwal'])
        self.assertEqual(info['thu'], 'Thứ Tư')
        self.assertEqual(info['tanggal'], '2026-09-09')  # Thứ 4 tuần kế tiếp
        self.assertEqual(info['buoi_so'], 5)             # Mốc buoi_bat_dau

    # =========================================================================
    # QUY TẮC 4: 2 lớp cùng ngày khác khung giờ -> Khung sớm hiện trước,
    # kết thúc khung sớm thì tự động chuyển sang hiện lớp có khung muộn hơn
    # =========================================================================
    @patch('database.get_buoi_hoc_hien_tai_cua_lop', return_value=1)
    @patch('database._now_app')
    @patch('database.get_connection')
    def test_rule_4_same_day_different_time_slots_auto_transitions(self, mock_conn, mock_now, mock_buoi):
        jadwal_sang = {
            'id': 101, 'hari': 'Senin', 'jam_mulai': '07:00:00', 'jam_selesai': '11:30:00',
            'nama_kelas': 'Lớp Ca Sáng', 'nama_mk': 'Môn Sáng', 'kode_mk': 'SANG',
            'kelas_id': 21, 'buoi_bat_dau': 1, 'batas_terlambat': None
        }
        jadwal_chieu = {
            'id': 102, 'hari': 'Senin', 'jam_mulai': '13:00:00', 'jam_selesai': '17:30:00',
            'nama_kelas': 'Lớp Ca Chiều', 'nama_mk': 'Môn Chiều', 'kode_mk': 'CHIEU',
            'kelas_id': 22, 'buoi_bat_dau': 1, 'batas_terlambat': None
        }
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [jadwal_chieu, jadwal_sang]
        mock_conn.return_value.cursor.return_value = mock_cursor
        tz = ZoneInfo("Asia/Jakarta")

        # 1. Lúc 06:30 (trước ca sáng) -> Hiện Lớp Ca Sáng
        mock_now.return_value = datetime(2026, 9, 7, 6, 30, 0, tzinfo=tz)
        info_0630 = database.get_thong_tin_buoi_hoc_hom_nay()
        self.assertEqual(info_0630['nama_kelas'], 'Lớp Ca Sáng')
        self.assertEqual(info_0630['jam_mulai'], '07:00')

        # 2. Lúc 08:30 (đang học ca sáng) -> Hiện Lớp Ca Sáng (đang diễn ra)
        mock_now.return_value = datetime(2026, 9, 7, 8, 30, 0, tzinfo=tz)
        info_0830 = database.get_thong_tin_buoi_hoc_hom_nay()
        self.assertEqual(info_0830['nama_kelas'], 'Lớp Ca Sáng')
        self.assertTrue(info_0830['is_ongoing'])

        # 3. Lúc 12:00 (kết thúc ca sáng 11:30, trước ca chiều) -> TỰ ĐỘNG CHUYỂN SANG Lớp Ca Chiều!
        mock_now.return_value = datetime(2026, 9, 7, 12, 0, 0, tzinfo=tz)
        info_1200 = database.get_thong_tin_buoi_hoc_hom_nay()
        self.assertEqual(info_1200['nama_kelas'], 'Lớp Ca Chiều')
        self.assertEqual(info_1200['jam_mulai'], '13:00')
        self.assertEqual(info_1200['tanggal'], '2026-09-07')

        # 4. Lúc 15:00 (đang học ca chiều) -> Hiện Lớp Ca Chiều
        mock_now.return_value = datetime(2026, 9, 7, 15, 0, 0, tzinfo=tz)
        info_1500 = database.get_thong_tin_buoi_hoc_hom_nay()
        self.assertEqual(info_1500['nama_kelas'], 'Lớp Ca Chiều')
        self.assertTrue(info_1500['is_ongoing'])

        # 5. Lúc 18:00 (cả 2 ca Thứ Hai kết thúc) -> Tuần sau ca sáng lại hiện trước
        mock_now.return_value = datetime(2026, 9, 7, 18, 0, 0, tzinfo=tz)
        info_1800 = database.get_thong_tin_buoi_hoc_hom_nay()
        self.assertEqual(info_1800['nama_kelas'], 'Lớp Ca Sáng')
        self.assertEqual(info_1800['tanggal'], '2026-09-14')

    # =========================================================================
    # QUY TẮC 5: 1 lớp có nhiều buổi trong tuần -> Tự động lấy buổi sắp tới gần nhất
    # =========================================================================
    @patch('database.get_buoi_hoc_hien_tai_cua_lop', return_value=1)
    @patch('database._now_app')
    @patch('database.get_connection')
    def test_rule_5_class_with_multiple_sessions_picks_nearest_upcoming(self, mock_conn, mock_now, mock_buoi):
        # Lớp ML-02 học Thứ 4 (06:00) và Thứ 7 (13:00)
        jadwal_t4 = {
            'id': 201, 'hari': 'Rabu', 'jam_mulai': '06:00:00', 'jam_selesai': '12:00:00',
            'nama_kelas': 'ML-02', 'nama_mk': 'Machine Learning', 'kode_mk': 'ML02',
            'kelas_id': 30, 'buoi_bat_dau': 1, 'batas_terlambat': None
        }
        jadwal_t7 = {
            'id': 202, 'hari': 'Sabtu', 'jam_mulai': '13:00:00', 'jam_selesai': '17:00:00',
            'nama_kelas': 'ML-02', 'nama_mk': 'Machine Learning', 'kode_mk': 'ML02',
            'kelas_id': 30, 'buoi_bat_dau': 1, 'batas_terlambat': None
        }
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [jadwal_t4, jadwal_t7]
        mock_conn.return_value.cursor.return_value = mock_cursor
        tz = ZoneInfo("Asia/Jakarta")

        # 1. Hôm nay Thứ Ba 08/09/2026 -> Buổi gần nhất là Thứ Tư 09/09/2026
        mock_now.return_value = datetime(2026, 9, 8, 10, 0, 0, tzinfo=tz)
        info_tue = database.get_thong_tin_buoi_hoc_hom_nay(kelas_id_filter=30)
        self.assertEqual(info_tue['thu'], 'Thứ Tư')
        self.assertEqual(info_tue['tanggal'], '2026-09-09')

        # 2. Hôm nay Thứ Năm 10/09/2026 -> Buổi gần nhất là Thứ Bảy 12/09/2026
        mock_now.return_value = datetime(2026, 9, 10, 10, 0, 0, tzinfo=tz)
        info_thu = database.get_thong_tin_buoi_hoc_hom_nay(kelas_id_filter=30)
        self.assertEqual(info_thu['thu'], 'Thứ Bảy')
        self.assertEqual(info_thu['tanggal'], '2026-09-12')

        # 3. Hôm nay Chủ Nhật 13/09/2026 -> Buổi gần nhất là Thứ Tư tuần sau 16/09/2026
        mock_now.return_value = datetime(2026, 9, 13, 10, 0, 0, tzinfo=tz)
        info_sun = database.get_thong_tin_buoi_hoc_hom_nay(kelas_id_filter=30)
        self.assertEqual(info_sun['thu'], 'Thứ Tư')
        self.assertEqual(info_sun['tanggal'], '2026-09-16')

    # =========================================================================
    # QUY TẮC 6: Drop list đại diện lớp bằng buổi sắp tới gần nhất
    # =========================================================================
    @patch('database.get_buoi_hoc_hien_tai_cua_lop', return_value=1)
    @patch('database._now_app')
    @patch('database.get_connection')
    def test_rule_6_drop_list_represents_class_by_nearest_session(self, mock_conn, mock_now, mock_buoi):
        jadwal_t4 = {
            'id': 201, 'hari': 'Rabu', 'jam_mulai': '06:00:00', 'jam_selesai': '12:00:00',
            'nama_kelas': 'ML-02', 'nama_mk': 'Machine Learning', 'kode_mk': 'ML02',
            'kelas_id': 30, 'buoi_bat_dau': 1, 'batas_terlambat': None
        }
        jadwal_t7 = {
            'id': 202, 'hari': 'Sabtu', 'jam_mulai': '13:00:00', 'jam_selesai': '17:00:00',
            'nama_kelas': 'ML-02', 'nama_mk': 'Machine Learning', 'kode_mk': 'ML02',
            'kelas_id': 30, 'buoi_bat_dau': 1, 'batas_terlambat': None
        }
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [jadwal_t4, jadwal_t7]
        mock_conn.return_value.cursor.return_value = mock_cursor
        tz = ZoneInfo("Asia/Jakarta")

        # Vào Thứ Năm: Drop list của ML-02 đại diện bằng ca Thứ Bảy (jadwal_id 202)
        mock_now.return_value = datetime(2026, 9, 10, 10, 0, 0, tzinfo=tz)
        info = database.get_thong_tin_buoi_hoc_hom_nay()
        dropdown = info['danh_sach_lop']
        self.assertEqual(len(dropdown), 1)
        self.assertEqual(dropdown[0]['jadwal_id'], 202)
        self.assertEqual(dropdown[0]['thu'], 'Thứ Bảy')

if __name__ == '__main__':
    unittest.main()
