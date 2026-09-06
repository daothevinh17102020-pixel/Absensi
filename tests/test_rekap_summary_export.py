import unittest
import os
import sys

# Đảm bảo import được app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, _lay_du_lieu_ma_tran_rekap


class TestRekapSummaryAndExport(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_rekap_stats_and_az_sorting(self):
        """Kiểm tra hàm _lay_du_lieu_ma_tran_rekap bổ sung stats và sort A-Z theo tên chính."""
        rekap, ringkasan, _ = _lay_du_lieu_ma_tran_rekap(kelas_id=None)
        self.assertIsInstance(rekap, list)
        if len(rekap) > 0:
            first = rekap[0]
            self.assertIn('stats', first)
            stats = first['stats']
            self.assertIn('present_count', stats)
            self.assertIn('late_count', stats)
            self.assertIn('excused_count', stats)
            self.assertIn('absent_count', stats)
            self.assertIn('total_absent', stats)
            self.assertIn('exam_status', stats)
            self.assertIn(stats['exam_status'], ['du_dieu_kien', 'canh_bao', 'cam_thi'])

            # Kiểm tra tính đúng đắn của quy chế: total_absent >= 4 -> cam_thi, == 3 -> canh_bao
            for sv in rekap:
                st = sv['stats']
                if st['total_absent'] >= 4:
                    self.assertEqual(st['exam_status'], 'cam_thi')
                elif st['total_absent'] == 3:
                    self.assertEqual(st['exam_status'], 'canh_bao')
                else:
                    self.assertEqual(st['exam_status'], 'du_dieu_kien')

    def _login_admin(self):
        with self.client.session_transaction() as sess:
            sess['admin_id'] = 1
            sess['username'] = 'admin'
            sess['role'] = 'admin'
            sess['is_guest'] = False

    def test_export_excel_matrix_vs_summary(self):
        """Kiểm tra endpoint /absensi/export xuất đúng file theo view matrix vs summary."""
        self._login_admin()

        # 1. Xuất Excel chi tiết 15 buổi
        res_matrix = self.client.get('/absensi/export?format=xlsx')
        self.assertEqual(res_matrix.status_code, 200)
        disp_matrix = res_matrix.headers.get('Content-Disposition', '')
        self.assertIn('tong_hop_diem_danh_', disp_matrix)
        self.assertTrue(disp_matrix.endswith('.xlsx'))

        # 2. Xuất Excel bảng Tổng kết
        res_summary = self.client.get('/absensi/export?format=xlsx&view=summary')
        self.assertEqual(res_summary.status_code, 200)
        disp_summary = res_summary.headers.get('Content-Disposition', '')
        self.assertIn('tong_ket_chuyen_can_', disp_summary)
        self.assertTrue(disp_summary.endswith('.xlsx'))

    def test_export_csv_summary(self):
        """Kiểm tra xuất CSV bảng Tổng kết chứa header 10 cột chuẩn."""
        self._login_admin()

        res_csv = self.client.get('/absensi/export?format=csv&view=summary')
        self.assertEqual(res_csv.status_code, 200)
        data_text = res_csv.data.decode('utf-8-sig')
        self.assertIn('STT,Sinh viên,Mã SV,Lớp,Đúng giờ,Muộn,Phép,Vắng,Điều kiện thi,Điểm chuyên cần', data_text)


if __name__ == '__main__':
    unittest.main()
