import unittest
from unittest.mock import patch, MagicMock
import app

class Gap12AutoAlphaTests(unittest.TestCase):
    @patch('app.db')
    def test_absent_student_auto_marked_alpha_for_past_sessions(self, mock_db):
        # Giả lập:
        # Lớp 1 có 2 sinh viên: SV 101 (đi học Buổi 1 & 2), SV 102 (chỉ đi Buổi 1, nghỉ Buổi 2)
        # SV 103 (chưa đi buổi nào bao giờ)
        mock_db.get_semua_jadwal.return_value = [{'id': 1, 'kelas_id': 1}]
        mock_db.get_ringkasan_rekap.return_value = {'hadir': 3, 'terlambat': 0, 'izin': 0, 'sakit': 0, 'alpha': 0}
        
        # Raw rekap chỉ ghi nhận:
        # SV 101: Buổi 1 (hadir), Buổi 2 (hadir)
        # SV 102: Buổi 1 (hadir) -> Buổi 2 vắng, không có record!
        mock_db.get_rekap_absensi.return_value = [
            {'user_id': 101, 'buoi_so': 1, 'status': 'hadir', 'kelas_id': 1, 'jadwal_id': 1},
            {'user_id': 101, 'buoi_so': 2, 'status': 'hadir', 'kelas_id': 1, 'jadwal_id': 1},
            {'user_id': 102, 'buoi_so': 1, 'status': 'hadir', 'kelas_id': 1, 'jadwal_id': 1},
        ]
        
        mock_db.get_users_by_kelas.return_value = [
            {'id': 101, 'nama': 'Sinh Vien A', 'nim': 'SV01', 'kelas_id': 1, 'nama_kelas': 'Lớp 1'},
            {'id': 102, 'nama': 'Sinh Vien B', 'nim': 'SV02', 'kelas_id': 1, 'nama_kelas': 'Lớp 1'},
            {'id': 103, 'nama': 'Sinh Vien C', 'nim': 'SV03', 'kelas_id': 1, 'nama_kelas': 'Lớp 1'},
        ]

        rekap, ringkasan, _ = app._lay_du_lieu_ma_tran_rekap(kelas_id=1)

        # Tìm từng SV trong kết quả
        rekap_by_id = {s['id']: s for s in rekap}

        # 1. SV 101: Đi cả Buổi 1 & 2 -> Buổi 1, 2 đều 'hadir', Buổi 3+ là None
        sv101 = rekap_by_id[101]
        self.assertEqual(sv101['sessions'][1], 'hadir')
        self.assertEqual(sv101['sessions'][2], 'hadir')
        self.assertIsNone(sv101['sessions'][3])

        # 2. SV 102: Buổi 1 có mặt ('hadir'), Buổi 2 không có record -> Tự động chốt 'alpha'
        sv102 = rekap_by_id[102]
        self.assertEqual(sv102['sessions'][1], 'hadir')
        self.assertEqual(sv102['sessions'][2], 'alpha', "Buổi 2 SV 102 không có record phải tự động chốt alpha")
        self.assertIsNone(sv102['sessions'][3], "Buổi 3 chưa học phải là None")

        # 3. SV 103: Nghỉ cả 2 buổi đã diễn ra -> Buổi 1 & 2 đều tự động 'alpha'
        sv103 = rekap_by_id[103]
        self.assertEqual(sv103['sessions'][1], 'alpha', "Buổi 1 SV 103 phải tự động chốt alpha")
        self.assertEqual(sv103['sessions'][2], 'alpha', "Buổi 2 SV 103 phải tự động chốt alpha")
        self.assertIsNone(sv103['sessions'][3], "Buổi 3 chưa học phải là None")

    @patch('app.db')
    def test_multi_class_isolation_for_auto_alpha(self, mock_db):
        # Kiểm tra tính cô lập giữa 2 lớp:
        # Lớp 1 đã học Buổi 3
        # Lớp 2 mới học Buổi 1
        mock_db.get_semua_jadwal.return_value = [
            {'id': 1, 'kelas_id': 1},
            {'id': 2, 'kelas_id': 2}
        ]
        mock_db.get_ringkasan_rekap.return_value = {}
        mock_db.get_rekap_absensi.return_value = [
            {'user_id': 201, 'buoi_so': 3, 'status': 'hadir', 'kelas_id': 1},
            {'user_id': 202, 'buoi_so': 1, 'status': 'hadir', 'kelas_id': 2},
        ]
        mock_db.get_semua_user.return_value = [
            {'id': 201, 'nama': 'SV Lop 1', 'nim': 'SV201', 'kelas_id': 1, 'nama_kelas': 'Lớp 1'},
            {'id': 202, 'nama': 'SV Lop 2', 'nim': 'SV202', 'kelas_id': 2, 'nama_kelas': 'Lớp 2'},
        ]

        rekap, _, _ = app._lay_du_lieu_ma_tran_rekap(kelas_id=None)
        rekap_by_id = {s['id']: s for s in rekap}

        # SV 202 thuộc Lớp 2 (lớp mới học đến buổi 1)
        # Buổi 2 và Buổi 3 của Lớp 2 CHƯA DIỄN RA -> Không được đánh vắng SV 202 ở buổi 2, 3
        sv202 = rekap_by_id[202]
        self.assertEqual(sv202['sessions'][1], 'hadir')
        self.assertIsNone(sv202['sessions'][2], "Lớp 2 chưa học Buổi 2, không được đánh vắng")
        self.assertIsNone(sv202['sessions'][3], "Lớp 2 chưa học Buổi 3, không được đánh vắng")

if __name__ == '__main__':
    unittest.main()
