import os
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

import app
import database
from face import recognition


class TrackerTests(unittest.TestCase):
    def setUp(self):
        app._consecutive_trackers.clear()

    def test_trackers_are_isolated_per_client(self):
        self.assertEqual(app._update_consecutive_tracker('camera-a', 1), 1)
        self.assertEqual(app._update_consecutive_tracker('camera-a', 1), 2)
        self.assertEqual(app._update_consecutive_tracker('camera-b', 2), 1)
        self.assertEqual(app._update_consecutive_tracker('camera-a', 1), 3)

    def test_unknown_frame_never_makes_count_negative(self):
        self.assertEqual(app._update_consecutive_tracker('camera-a'), 0)

    def test_multiple_users_accumulate_independently_in_same_camera(self):
        self.assertEqual(
            app._sync_consecutive_trackers('camera-a', [1, 2]),
            {1: 1, 2: 1}
        )
        self.assertEqual(
            app._sync_consecutive_trackers('camera-a', [1, 2]),
            {1: 2, 2: 2}
        )

    def test_same_identity_at_non_overlapping_location_starts_new_track(self):
        first = app._sync_face_trackers(
            'camera-a', {1: (0, 0, 80, 80)}
        )
        moved_to_other_face = app._sync_face_trackers(
            'camera-a', {1: (160, 0, 80, 80)}
        )
        same_track = app._sync_face_trackers(
            'camera-a', {1: (165, 0, 80, 80)}
        )

        self.assertEqual(first[1], 1)
        self.assertEqual(moved_to_other_face[1], 1)
        self.assertEqual(same_track[1], 2)

    def test_same_track_cannot_inherit_count_from_another_identity(self):
        first = app._sync_face_trackers(
            'camera-a', {7: {'user_id': 1, 'bbox': (0, 0, 80, 80)}}
        )
        second = app._sync_face_trackers(
            'camera-a', {7: {'user_id': 1, 'bbox': (2, 0, 80, 80)}}
        )
        switched = app._sync_face_trackers(
            'camera-a', {7: {'user_id': 2, 'bbox': (4, 0, 80, 80)}}
        )

        self.assertEqual(first[7], 1)
        self.assertEqual(second[7], 2)
        self.assertEqual(switched[7], 1)

    def test_missing_frame_resets_consecutive_evidence(self):
        app._sync_face_trackers(
            'camera-a', {7: {'user_id': 1, 'bbox': (0, 0, 80, 80)}}
        )
        app._sync_face_trackers('camera-a', {})
        resumed = app._sync_face_trackers(
            'camera-a', {7: {'user_id': 1, 'bbox': (1, 0, 80, 80)}}
        )

        self.assertEqual(resumed[7], 1)


class RecognitionFlowTests(unittest.TestCase):
    def setUp(self):
        app._consecutive_trackers.clear()

    @patch('face.recognition.predict')
    @patch('face.anti_spoofing.check_face')
    @patch.object(app.db, 'get_user_by_id')
    @patch.object(app.db, 'get_jadwal_aktif')
    def test_active_schedule_is_requeried_for_each_verified_attempt(
        self, get_jadwal_aktif, get_user_by_id, spoofing_check, predict
    ):
        spoofing_check.return_value = {
            'is_real': True, 'label': 'REAL', 'score': 1.0
        }
        predict.return_value = [{
            'user_id': 1, 'confidence': 40.0, 'dikenali': True,
            'bbox': (0, 0, 100, 100)
        }]
        get_user_by_id.return_value = {
            'id': 1, 'nama': 'Test', 'nim': '001',
            'kelas_id': 1, 'nama_kelas': 'ML-01'
        }
        get_jadwal_aktif.return_value = []

        with patch.object(app, 'RECOGNITION_REQUIRED_FRAMES', 1):
            first = app._proses_recognition(object(), tracker_key='camera-a')
            second = app._proses_recognition(object(), tracker_key='camera-a')

        self.assertEqual(first['tipe'], 'no_jadwal')
        self.assertEqual(second['tipe'], 'no_jadwal')
        self.assertEqual(get_jadwal_aktif.call_count, 2)

    @patch.object(app, '_simpan_snapshot')
    @patch.object(app.db, 'catat_absensi')
    @patch.object(app.db, 'get_user_by_id')
    def test_multiple_active_schedules_for_one_class_fail_closed(
        self, get_user_by_id, catat_absensi, save_snapshot
    ):
        get_user_by_id.return_value = {
            'id': 1, 'nama': 'Test', 'nim': '001', 'kelas_id': 9,
            'nama_kelas': 'ML-01',
        }
        result = app._process_verified_prediction(
            object(), {'user_id': 1, 'confidence': 0.9},
            {'is_real': True, 'label': 'REAL', 'score': 1.0},
            'Senin', '08:00:00', date(2026, 8, 24), [
                {'id': 7, 'kelas_id': 9, 'nama_mk': 'Machine Learning'},
                {'id': 8, 'kelas_id': 9, 'nama_mk': 'Data Mining'},
            ],
        )

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['tipe'], 'multiple_active_schedules')
        catat_absensi.assert_not_called()
        save_snapshot.assert_not_called()

    @patch.object(app, '_simpan_snapshot', return_value='snapshots/group.jpg')
    @patch.object(app.db, 'get_statistik_dashboard')
    @patch.object(app.db, 'catat_absensi')
    @patch.object(app.db, 'cek_sudah_absen', return_value=None)
    @patch.object(app.db, 'get_jadwal_aktif')
    @patch.object(app.db, 'get_user_by_id')
    @patch('face.anti_spoofing.check_face')
    @patch('face.recognition.predict')
    def test_one_frame_can_record_two_distinct_students(
        self, predict, check_face, get_user_by_id, get_jadwal_aktif,
        _cek_sudah_absen, catat_absensi, get_stats, _save_snapshot
    ):
        predict.return_value = [
            {'user_id': 1, 'confidence': 31.0, 'dikenali': True,
             'bbox': (0, 0, 80, 80)},
            {'user_id': 2, 'confidence': 38.0, 'dikenali': True,
             'bbox': (100, 0, 80, 80)}
        ]
        check_face.return_value = {'is_real': True, 'label': 'REAL', 'score': 1.0}
        users = {
            1: {'id': 1, 'nama': 'A', 'nim': '001', 'kelas_id': 9,
                'nama_kelas': 'ML-01'},
            2: {'id': 2, 'nama': 'B', 'nim': '002', 'kelas_id': 9,
                'nama_kelas': 'ML-01'}
        }
        get_user_by_id.side_effect = lambda uid: users[uid]
        get_jadwal_aktif.return_value = [{
            'id': 7, 'kelas_id': 9, 'nama_mk': 'Machine Learning',
            'batas_terlambat': '23:59:59'
        }]
        catat_absensi.side_effect = [101, 102]
        get_stats.return_value = {
            'hadir_hari_ini': 2, 'terlambat_hari_ini': 0, 'alpha_hari_ini': 0
        }

        with patch.object(app, 'RECOGNITION_REQUIRED_FRAMES', 1):
            result = app._proses_recognition(object(), tracker_key='group-camera')

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['summary']['recorded'], 2)
        self.assertEqual(len(result['results']), 2)
        self.assertEqual(catat_absensi.call_count, 2)
        recorded_ids = [call.kwargs['user_id'] for call in catat_absensi.call_args_list]
        self.assertEqual(recorded_ids, [1, 2])

    @patch.object(app, '_simpan_snapshot', return_value='snapshots/group-10.jpg')
    @patch.object(app.db, 'get_statistik_dashboard')
    @patch.object(app.db, 'catat_absensi')
    @patch.object(app.db, 'cek_sudah_absen', return_value=None)
    @patch.object(app.db, 'get_jadwal_aktif')
    @patch.object(app.db, 'get_user_by_id')
    @patch('face.anti_spoofing.check_face')
    @patch('face.recognition.predict')
    def test_ten_students_verify_independently_on_third_frame(
        self, predict, check_face, get_user_by_id, get_jadwal_aktif,
        _cek_sudah_absen, catat_absensi, get_stats, _save_snapshot
    ):
        predict.return_value = [
            {
                'user_id': user_id, 'track_id': 100 + user_id,
                'confidence': 0.85, 'match_score': 0.85,
                'dikenali': True, 'recognition_status': 'recognized',
                'bbox': ((user_id - 1) * 90, 0, 80, 80),
                'detector_score': 0.99 - user_id / 100,
            }
            for user_id in range(1, 11)
        ]
        check_face.return_value = {'is_real': True, 'label': 'REAL', 'score': 1.0}
        get_user_by_id.side_effect = lambda user_id: {
            'id': user_id, 'nama': f'Student {user_id}', 'nim': f'{user_id:03d}',
            'kelas_id': 9, 'nama_kelas': 'ML-01',
        }
        get_jadwal_aktif.return_value = [{
            'id': 7, 'kelas_id': 9, 'nama_mk': 'Machine Learning',
            'batas_terlambat': '23:59:59',
        }]
        catat_absensi.side_effect = list(range(101, 111))
        get_stats.return_value = {
            'hadir_hari_ini': 10, 'terlambat_hari_ini': 0, 'alpha_hari_ini': 0,
        }

        with patch.object(app, 'RECOGNITION_REQUIRED_FRAMES', 3):
            first = app._proses_recognition(object(), tracker_key='group-10')
            second = app._proses_recognition(object(), tracker_key='group-10')
            third = app._proses_recognition(object(), tracker_key='group-10')

        self.assertEqual(first['summary']['verifying'], 10)
        self.assertEqual(second['summary']['verifying'], 10)
        self.assertEqual(third['summary']['recorded'], 10)
        self.assertEqual(catat_absensi.call_count, 10)
        self.assertEqual(check_face.call_count, 10)

    @patch.object(app.db, 'get_jadwal_aktif', return_value=[])
    @patch.object(app.db, 'get_user_by_id')
    @patch('face.anti_spoofing.check_face')
    @patch('face.recognition.predict')
    def test_anti_spoofing_runs_only_after_required_frames(
        self, predict, check_face, get_user_by_id, _get_jadwal_aktif
    ):
        predict.return_value = [{
            'user_id': 1, 'track_id': 11, 'confidence': 0.85,
            'match_score': 0.85, 'dikenali': True,
            'recognition_status': 'recognized', 'bbox': (0, 0, 100, 100),
            'detector_score': 0.95,
        }]
        check_face.return_value = {'is_real': True, 'label': 'REAL', 'score': 1.0}
        get_user_by_id.return_value = {
            'id': 1, 'nama': 'A', 'nim': '001', 'kelas_id': 9,
            'nama_kelas': 'ML-01',
        }

        with patch.object(app, 'RECOGNITION_REQUIRED_FRAMES', 3):
            first = app._proses_recognition(object(), tracker_key='deferred-liveness')
            second = app._proses_recognition(object(), tracker_key='deferred-liveness')
            self.assertEqual(check_face.call_count, 0)
            third = app._proses_recognition(object(), tracker_key='deferred-liveness')

        self.assertEqual(first['tipe'], 'verifying')
        self.assertEqual(second['tipe'], 'verifying')
        self.assertEqual(third['tipe'], 'no_jadwal')
        check_face.assert_called_once()

    @patch.object(app, '_simpan_snapshot', return_value='snapshots/group.jpg')
    @patch.object(app.db, 'get_statistik_dashboard', return_value={})
    @patch.object(app.db, 'catat_absensi', return_value=101)
    @patch.object(app.db, 'cek_sudah_absen', return_value=None)
    @patch.object(app.db, 'get_jadwal_aktif')
    @patch.object(app.db, 'get_user_by_id')
    @patch('face.anti_spoofing.check_face')
    @patch('face.recognition.predict')
    def test_duplicate_identity_in_same_frame_is_blocked_for_all_faces(
        self, predict, check_face, get_user_by_id, get_jadwal_aktif,
        _cek_sudah_absen, catat_absensi, _get_stats, _save_snapshot
    ):
        predict.return_value = [
            {'user_id': 1, 'confidence': 30.0, 'dikenali': True,
             'bbox': (0, 0, 80, 80)},
            {'user_id': 1, 'confidence': 55.0, 'dikenali': True,
             'bbox': (100, 0, 80, 80)}
        ]
        check_face.return_value = {'is_real': True, 'label': 'REAL', 'score': 1.0}
        get_user_by_id.return_value = {
            'id': 1, 'nama': 'A', 'nim': '001', 'kelas_id': 9,
            'nama_kelas': 'ML-01'
        }
        get_jadwal_aktif.return_value = [{
            'id': 7, 'kelas_id': 9, 'nama_mk': 'Machine Learning',
            'batas_terlambat': '23:59:59'
        }]

        with patch.object(app, 'RECOGNITION_REQUIRED_FRAMES', 1):
            result = app._proses_recognition(object(), tracker_key='group-camera')

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['summary']['recorded'], 0)
        self.assertEqual(result['summary']['identity_conflicts'], 2)
        catat_absensi.assert_not_called()

    @patch.object(app, '_simpan_snapshot', return_value='snapshots/mixed.jpg')
    @patch.object(app.db, 'catat_spoofing', return_value=11)
    @patch.object(app.db, 'get_statistik_dashboard', return_value={})
    @patch.object(app.db, 'catat_absensi', return_value=101)
    @patch.object(app.db, 'cek_sudah_absen', return_value=None)
    @patch.object(app.db, 'get_jadwal_aktif')
    @patch.object(app.db, 'get_user_by_id')
    @patch('face.anti_spoofing.check_face')
    @patch('face.recognition.predict')
    def test_unknown_and_spoof_faces_do_not_block_valid_student(
        self, predict, check_face, get_user_by_id, get_jadwal_aktif,
        _cek_sudah_absen, catat_absensi, _get_stats, catat_spoofing,
        _save_snapshot
    ):
        predict.return_value = [
            {'user_id': 9, 'confidence': 140.0, 'dikenali': False,
             'bbox': (0, 0, 60, 60)},
            {'user_id': 8, 'confidence': 35.0, 'dikenali': True,
             'bbox': (70, 0, 60, 60)},
            {'user_id': 2, 'confidence': 32.0, 'dikenali': True,
             'bbox': (140, 0, 60, 60)}
        ]
        # Liveness is deferred for unknown faces, therefore checks run only
        # for the two recognized tracks below.
        check_face.side_effect = [
            {'is_real': False, 'label': 'SPOOFING', 'score': 0.2},
            {'is_real': True, 'label': 'REAL', 'score': 1.0}
        ]
        get_user_by_id.return_value = {
            'id': 2, 'nama': 'B', 'nim': '002', 'kelas_id': 9,
            'nama_kelas': 'ML-01'
        }
        get_jadwal_aktif.return_value = [{
            'id': 7, 'kelas_id': 9, 'nama_mk': 'Machine Learning',
            'batas_terlambat': '23:59:59'
        }]

        with patch.object(app, 'RECOGNITION_REQUIRED_FRAMES', 1):
            result = app._proses_recognition(object(), tracker_key='mixed-camera')

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['summary']['recorded'], 1)
        self.assertEqual(result['summary']['unknown'], 1)
        self.assertEqual(result['summary']['spoofing'], 1)
        catat_absensi.assert_called_once()
        catat_spoofing.assert_called_once()


class RecognitionEngineTests(unittest.TestCase):
    def test_cosine_gallery_uses_best_template_for_each_user(self):
        with patch.object(recognition, '_gallery_ids', np.array([1, 1, 2])), \
             patch.object(recognition, '_gallery_embeddings', np.array([
                 [0.70, 0.70], [1.0, 0.0], [0.0, 1.0]
             ], dtype=np.float32)):
            user_id, score = recognition._match_embedding(np.array([1.0, 0.0]))

        self.assertEqual(user_id, 1)
        self.assertAlmostEqual(score, 1.0)

    def test_empty_gallery_cannot_match_any_identity(self):
        with patch.object(recognition, '_gallery_ids', np.empty((0,), dtype=np.int64)):
            self.assertEqual(recognition._match_embedding(np.array([1.0, 0.0])), (None, None))

    def test_match_details_exposes_runner_up_for_ambiguous_match_rejection(self):
        with patch.object(recognition, '_gallery_ids', np.array([1, 2])), \
             patch.object(recognition, '_gallery_embeddings', np.array([
                 [1.0, 0.0], [0.999, 0.045]
             ], dtype=np.float32)):
            user_id, score, runner_id, runner_score = recognition._match_embedding_details(
                np.array([1.0, 0.0])
            )
        self.assertEqual(user_id, 1)
        self.assertEqual(runner_id, 2)
        self.assertGreater(score, runner_score)
        self.assertLess(score - runner_score, 0.01)


class FaceDisplayMetadataTests(unittest.TestCase):
    def test_unknown_face_metadata_is_red_and_keeps_match_score(self):
        result = app._attach_face_metadata(
            {'status': 'error', 'tipe': 'unknown'},
            {'bbox': (1, 2, 3, 4), 'match_score': 0.321, 'user_id': 7},
            0,
        )
        self.assertEqual(result['display_status'], 'error')
        self.assertIn('Không khớp', result['display_label'])
        self.assertEqual(result['match_score'], 0.321)

    def test_success_label_shows_name_and_nim_without_internal_score(self):
        result = app._attach_face_metadata(
            {'status': 'ok', 'data': {'nama': 'DAO VINH', 'nim': '24D400056'}},
            {
                'bbox': (1, 2, 3, 4), 'track_id': 9, 'user_id': 77,
                'match_score': 0.785,
            },
            0,
        )

        self.assertEqual(result['display_status'], 'recognized')
        self.assertEqual(result['display_label'], 'DAO VINH — 24D400056')
        self.assertNotIn('0.785', result['display_label'])
        self.assertNotIn('77', result['display_label'])

    def test_verifying_label_shows_progress_without_name_or_score(self):
        result = app._attach_face_metadata(
            {
                'status': 'skip', 'tipe': 'verifying',
                'verification_count': 2, 'required_frames': 3,
            },
            {
                'bbox': (1, 2, 3, 4), 'track_id': 9, 'user_id': 77,
                'match_score': 0.733,
            },
            0,
        )

        self.assertEqual(result['display_status'], 'warning')
        self.assertEqual(result['display_label'], 'Đang xác minh (2/3)')
        self.assertNotIn('77', result['display_label'])
        self.assertNotIn('0.733', result['display_label'])

    def test_multiple_active_schedules_metadata_is_a_warning(self):
        result = app._attach_face_metadata(
            {'status': 'error', 'tipe': 'multiple_active_schedules'},
            {'bbox': (1, 2, 3, 4)},
            0,
        )
        self.assertEqual(result['display_status'], 'warning')
        self.assertIn('Lịch học bị trùng', result['display_label'])


class RecognitionTransportTests(unittest.TestCase):
    def test_broadcast_sends_every_success_from_same_frame(self):
        result = {
            'status': 'ok',
            'stats': {'hadir': 2, 'terlambat': 0, 'alpha': 0},
            'results': [
                {'status': 'ok', 'data': {'nama': 'A', 'nim': '001'}},
                {'status': 'error', 'tipe': 'unknown'},
                {'status': 'ok', 'data': {'nama': 'B', 'nim': '002'}}
            ]
        }
        with patch.object(app.socketio, 'emit') as socket_emit:
            app._broadcast_absensi_updates(result)

        self.assertEqual(socket_emit.call_count, 2)
        payloads = [call.args[1] for call in socket_emit.call_args_list]
        self.assertEqual([item['nim'] for item in payloads], ['001', '002'])

    def test_socket_broadcast_can_exclude_originating_camera(self):
        result = {
            'status': 'ok',
            'data': {'nama': 'A', 'nim': '001'},
            'stats': {'hadir': 1, 'terlambat': 0, 'alpha': 0}
        }
        with patch.object(app.socketio, 'emit') as socket_emit:
            app._broadcast_absensi_updates(result, skip_sid='socket-camera-a')

        socket_emit.assert_called_once()
        self.assertEqual(socket_emit.call_args.kwargs['skip_sid'], 'socket-camera-a')

    @patch.object(app, 'emit')
    @patch.object(app, '_reset_consecutive_tracker')
    def test_socket_camera_stop_clears_its_tracker(self, reset_tracker, _emit):
        fake_request = Mock(sid='socket-camera-a')
        with patch.object(app, 'request', fake_request), \
             patch.object(app, 'session', {'admin_id': 7}):
            app.handle_camera_toggle({
                'active': False, 'client_id': 'camera_client_a'
            })

        reset_tracker.assert_called_once_with(
            'browser:7:camera_client_a', remove=True
        )


class SnapshotTests(unittest.TestCase):
    @patch.object(app.os, 'makedirs')
    @patch.object(app.cv2, 'imwrite', return_value=True)
    def test_snapshot_names_are_collision_resistant(self, _imwrite, _makedirs):
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        first = app._simpan_snapshot(frame, 1)
        second = app._simpan_snapshot(frame, 1)

        self.assertNotEqual(first, second)
        self.assertIn('1_', os.path.basename(first))

    @patch.object(app.os, 'remove')
    @patch.object(app.os.path, 'isfile', return_value=True)
    def test_failed_insert_snapshot_is_removed(self, _isfile, remove_file):
        snapshot_path = os.path.join(app.SNAPSHOT_PATH, 'orphan.jpg')
        app._hapus_snapshot_gagal(snapshot_path)

        remove_file.assert_called_once_with(os.path.realpath(snapshot_path))


class DatabaseCleanupTests(unittest.TestCase):
    def test_failed_attendance_insert_rolls_back_and_closes_connection(self):
        class Cursor:
            closed = False

            def execute(self, *_args, **_kwargs):
                raise RuntimeError('forced insert failure')

            def close(self):
                self.closed = True

        class Connection:
            rolled_back = False
            closed = False

            def __init__(self):
                self.db_cursor = Cursor()

            def cursor(self):
                return self.db_cursor

            def rollback(self):
                self.rolled_back = True

            def is_connected(self):
                return not self.closed

            def close(self):
                self.closed = True

        connection = Connection()
        with patch.object(database, 'get_connection', return_value=connection):
            result = database.catat_absensi(
                1, 1, date(2026, 8, 24), '08:00:00', 'hadir'
            )

        self.assertIsNone(result)
        self.assertTrue(connection.rolled_back)
        self.assertTrue(connection.db_cursor.closed)
        self.assertTrue(connection.closed)

    def test_failed_alpha_batch_rolls_back_and_closes_connection(self):
        class Cursor:
            rowcount = 0
            closed = False

            def execute(self, *_args, **_kwargs):
                raise RuntimeError('forced alpha insert failure')

            def close(self):
                self.closed = True

        class Connection:
            rolled_back = False
            closed = False

            def __init__(self):
                self.db_cursor = Cursor()

            def cursor(self):
                return self.db_cursor

            def rollback(self):
                self.rolled_back = True

            def is_connected(self):
                return not self.closed

            def close(self):
                self.closed = True

        connection = Connection()
        with patch.object(database, 'get_connection', return_value=connection):
            result = database.bulk_catat_alpha(1, [1], date(2026, 8, 24))

        self.assertEqual(result, 0)
        self.assertTrue(connection.rolled_back)
        self.assertTrue(connection.db_cursor.closed)
        self.assertTrue(connection.closed)


class SchedulePolicyTests(unittest.TestCase):
    def test_active_and_finished_queries_use_same_grace_period(self):
        cursor = Mock()
        cursor.fetchall.return_value = []
        connection = Mock()
        connection.cursor.return_value = cursor

        with patch.object(database, 'get_connection', return_value=connection):
            database.get_jadwal_aktif('Senin', '10:15:00')
            database.get_jadwal_selesai_hari_ini('Senin', '10:15:00')

        active_query = cursor.execute.call_args_list[0]
        finished_query = cursor.execute.call_args_list[1]
        self.assertIn('ORDER BY j.jam_mulai DESC', active_query.args[0])
        self.assertEqual(active_query.args[1][-1], database.ABSENSI_GRACE_MINUTES)
        self.assertEqual(finished_query.args[1][1], database.ABSENSI_GRACE_MINUTES)

    def test_ada_mahasiswa_hadir_jadwal_checks_valid_attendance(self):
        cursor = Mock()
        cursor.fetchone.return_value = (1,)
        connection = Mock()
        connection.cursor.return_value = cursor

        with patch.object(database, 'get_connection', return_value=connection):
            has_attendance = database.ada_mahasiswa_hadir_jadwal(12, date(2026, 9, 6))

        self.assertTrue(has_attendance)
        query, params = cursor.execute.call_args.args
        self.assertIn("status IN ('hadir', 'terlambat', 'izin', 'sakit')", query)
        self.assertEqual(params, (12, date(2026, 9, 6)))

    def test_kelas_sudah_ada_detects_existing_class(self):
        cursor = Mock()
        cursor.fetchone.return_value = (1,)
        connection = Mock()
        connection.cursor.return_value = cursor

        with patch.object(database, 'get_connection', return_value=connection):
            exists = database.kelas_sudah_ada('ML-01', '2026')

        self.assertTrue(exists)
        query, params = cursor.execute.call_args.args
        self.assertIn("nama_kelas = %s AND angkatan = %s", query)
        self.assertEqual(params, ('ML-01', '2026'))

    def test_matakuliah_memiliki_absensi_detects_attendance(self):
        cursor = Mock()
        cursor.fetchone.return_value = (1,)
        connection = Mock()
        connection.cursor.return_value = cursor

        with patch.object(database, 'get_connection', return_value=connection):
            has_absensi = database.matakuliah_memiliki_absensi(5)

        self.assertTrue(has_absensi)
        query, params = cursor.execute.call_args.args
        self.assertIn("j.matakuliah_id = %s", query)
        self.assertEqual(params, (5,))



class ReportingTests(unittest.TestCase):
    def test_empty_attendance_percentage_reports_zero_total(self):
        cursor = Mock()
        cursor.fetchall.return_value = []
        connection = Mock()
        connection.cursor.return_value = cursor

        with patch.object(database, 'get_connection', return_value=connection):
            result = database.get_persentase_kehadiran()

        self.assertEqual(result['total'], 0)
        self.assertEqual(result['hadir'], 0)

    def test_rekap_class_filter_uses_schedule_class_not_current_student_class(self):
        cursor = Mock()
        cursor.fetchall.return_value = []
        connection = Mock()
        connection.cursor.return_value = cursor

        with patch.object(database, 'get_connection', return_value=connection):
            database.get_rekap_absensi(kelas_id=7)

        query, params = cursor.execute.call_args.args
        self.assertIn('JOIN kelas k ON m.kelas_id = k.id', query)
        self.assertIn('AND m.kelas_id = %s', query)
        self.assertNotIn('AND u.kelas_id = %s', query)
        self.assertEqual(params, [7])


class ApiValidationTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        with self.client.session_transaction() as flask_session:
            flask_session['admin_id'] = 1

    def test_api_requires_json_authentication_response(self):
        client = app.app.test_client()
        response = client.get('/api/search?q=test')

        self.assertEqual(response.status_code, 401)
        self.assertTrue(response.is_json)
        self.assertEqual(response.get_json()['status'], 'error')

    def test_manual_attendance_rejects_non_object_and_invalid_ids(self):
        for payload in ([], 'text', True, {'user_id': 'abc', 'jadwal_id': 2,
                                           'status': 'hadir'}):
            response = self.client.post('/api/absensi/manual', json=payload)
            self.assertEqual(response.status_code, 400, payload)

    def test_photo_upload_rejects_wrong_string_field_types(self):
        response = self.client.post('/api/foto/upload', json={
            'nama': 123, 'nim': '001', 'kelas_id': 1,
            'foto': 'data:image/jpeg;base64,AA==', 'index': 0
        })

        self.assertEqual(response.status_code, 400)

    @patch.object(app.cv2, 'imdecode', return_value=np.zeros((100, 100, 3), dtype=np.uint8))
    @patch.object(app, '_quality_enrollment_upload', side_effect=RuntimeError('private-photo-error'))
    def test_photo_upload_failure_returns_retry_without_exposing_exception(self, _upload, _imdecode):
        response = self.client.post('/api/foto/upload', json={
            'nama': 'A', 'nim': '001', 'kelas_id': 1,
            'foto': 'data:image/jpeg;base64,AA==', 'index': 0,
            'protocol': 'quality_v1'
        })

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()['status'], 'retry')
        self.assertNotIn('private-photo-error', response.get_json()['pesan'])

    @patch.object(app.cv2, 'imdecode', return_value=np.zeros((100, 100, 3), dtype=np.uint8))
    @patch.object(app, '_quality_enrollment_upload')
    def test_photo_upload_rejects_legacy_protocol_without_writing(
        self, quality_upload, _imdecode
    ):
        response = self.client.post('/api/foto/upload', json={
            'nama': 'A', 'nim': '001', 'kelas_id': 1,
            'foto': 'data:image/jpeg;base64,AA==', 'index': 0
        })

        self.assertEqual(response.status_code, 400)
        quality_upload.assert_not_called()

    def test_camera_toggle_requires_boolean(self):
        response = self.client.post('/api/camera/toggle', json={
            'active': 'false', 'client_id': 'camera_test_id'
        })
        self.assertEqual(response.status_code, 400)

        response = self.client.post('/api/camera/toggle', json={
            'active': False, 'client_id': 'camera_test_id'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()['data']['camera_active'])

    @patch.object(app.db, 'get_absensi_hari_ini', side_effect=RuntimeError('secret'))
    def test_today_attendance_failure_is_500_without_exception_detail(self, _get_data):
        response = self.client.get('/api/absensi/hari-ini')
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('secret', response.get_json()['pesan'])

    @patch.object(app.db, 'get_ringkasan_rekap', return_value={})
    @patch.object(app.db, 'get_rekap_absensi', return_value=[])
    @patch.object(app.db, 'get_semua_matakuliah', return_value=[])
    @patch.object(app.db, 'get_semua_kelas', return_value=[])
    def test_filtered_recap_export_links_keep_all_query_parameters(
        self, _classes, _courses, _records, _summary
    ):
        response = self.client.get(
            '/absensi/rekap?kelas_id=7&matakuliah_id=9&dari=2026-01-01&sampai=2026-01-31'
        )
        html = response.get_data(as_text=True)
        self.assertIn('/absensi/export?format=csv&amp;kelas_id=7', html)
        self.assertIn('&amp;matakuliah_id=9', html)
        self.assertNotIn('format=csv?kelas_id', html)

    @patch.object(app.db, 'get_rekap_absensi')
    def test_csv_export_contains_utf8_bom_and_vietnamese_content(self, mock_rekap):
        mock_rekap.return_value = [
            {
                'nama': 'Nguyễn Văn A',
                'nim': '2026001',
                'nama_kelas': 'K58 Tin Học',
                'nama_mk': 'Học Máy',
                'kode_mk': 'ML01',
                'hari': 'Thứ Hai',
                'tanggal': '2026-09-06',
                'waktu_absen': '08:00:00',
                'status': 'hadir',
                'alasan': 'Đúng giờ',
            }
        ]
        response = self.client.get('/absensi/export?format=csv')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response.content_type)
        self.assertIn('charset=utf-8', response.content_type.lower())
        # Xác nhận có tiền tố UTF-8 BOM (0xEF, 0xBB, 0xBF) cho Microsoft Excel (GAP-07)
        self.assertTrue(
            response.data.startswith(b'\xef\xbb\xbf'),
            'CSV export must start with UTF-8 BOM (\\xef\\xbb\\xbf) for Excel compatibility'
        )
        content = response.data.decode('utf-8')
        self.assertIn('Họ và tên', content)
        self.assertIn('Thời gian điểm danh', content)
        self.assertIn('Nguyễn Văn A', content)
        self.assertIn('Thứ Hai', content)

    @patch.object(app.db, 'cari_mahasiswa', side_effect=RuntimeError('private-db-error'))
    def test_search_failure_is_500_without_exception_detail(self, _search):
        response = self.client.get('/api/search?q=test')
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('private-db-error', response.get_json()['pesan'])


    def test_student_search_propagates_failure_and_closes_resources(self):
        cursor = Mock()
        cursor.execute.side_effect = RuntimeError('query failed')
        connection = Mock()
        connection.cursor.return_value = cursor
        connection.is_connected.return_value = True

        with patch.object(database, 'get_connection', return_value=connection):
            with self.assertRaises(RuntimeError):
                database.cari_mahasiswa('test')

        cursor.close.assert_called_once_with()
        connection.close.assert_called_once_with()

    @patch.object(app, '_start_background_tasks_once')
    @patch.object(app.db, 'get_jadwal_by_id')
    @patch.object(app.db, 'get_user_by_id')
    def test_manual_attendance_rejects_student_from_another_class(
        self, get_user_by_id, get_jadwal_by_id, _start_background
    ):
        get_user_by_id.return_value = {'id': 1, 'nama': 'A', 'kelas_id': 10}
        get_jadwal_by_id.return_value = {
            'id': 2, 'kelas_id': 20, 'hari': app._get_nama_hari()
        }

        response = self.client.post('/api/absensi/manual', json={
            'user_id': 1, 'jadwal_id': 2, 'status': 'hadir', 'alasan': ''
        })

        self.assertEqual(response.status_code, 400)

    @patch.object(app, '_start_background_tasks_once')
    def test_photo_upload_rejects_non_numeric_index(self, _start_background):
        response = self.client.post('/api/foto/upload', json={
            'nama': 'A', 'nim': '001', 'kelas_id': 1,
            'foto': 'data:image/jpeg;base64,AA==', 'index': '../outside'
        })

        self.assertEqual(response.status_code, 400)

    @patch.object(app.db, 'tambah_user')
    @patch.object(app.db, 'get_user_by_nim')
    def test_invalid_first_photo_does_not_create_student(self, get_user, tambah_user):
        get_user.return_value = None
        response = self.client.post('/api/foto/upload', json={
            'nama': 'A', 'nim': '001', 'kelas_id': 1,
            'foto': 'data:image/jpeg;base64,AA==', 'index': 0
        })

        self.assertEqual(response.status_code, 400)
        get_user.assert_not_called()
        tambah_user.assert_not_called()

    @patch.object(app, '_broadcast_absensi_updates')
    @patch.object(app, '_proses_recognition')
    @patch.object(app, '_decode_frame')
    def test_http_recognition_uses_browser_client_id(
        self, decode_frame, process, broadcast_updates
    ):
        decode_frame.return_value = object()
        process.return_value = {'status': 'skip', 'data': None}

        first = self.client.post('/api/absensi/proses', json={
            'frame': 'x', 'client_id': 'camera_client_a'
        })
        second = self.client.post('/api/absensi/proses', json={
            'frame': 'x', 'client_id': 'camera_client_b'
        })

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        tracker_keys = [item.kwargs['tracker_key'] for item in process.call_args_list]
        self.assertEqual(tracker_keys, [
            'browser:1:camera_client_a', 'browser:1:camera_client_b'
        ])
        self.assertEqual(broadcast_updates.call_count, 2)
        broadcast_updates.assert_any_call(process.return_value)

    def test_existing_student_name_comparison_ignores_case_and_extra_spaces(self):
        self.assertEqual(
            app._normalize_student_name('Nguyen  Van A'),
            app._normalize_student_name('  nguyen van a '),
        )

    @patch.object(app.db, 'get_jadwal_hari', return_value=[])
    def test_today_schedule_api_uses_database_helper(self, get_jadwal_hari):
        response = self.client.get('/api/jadwal/hari-ini')

        self.assertEqual(response.status_code, 200)
        get_jadwal_hari.assert_called_once_with(app._get_nama_hari())


@unittest.skipUnless(os.environ.get('RUN_DB_TESTS') == '1', 'DB integration disabled')
class DatabaseSchemaIntegrationTests(unittest.TestCase):
    def test_attendance_has_unique_identity_schedule_date_constraint(self):
        conn = database.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT COLUMN_NAME
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME='absensi'
                  AND INDEX_NAME='uq_absensi' AND NON_UNIQUE=0
                ORDER BY SEQ_IN_INDEX
            """, (database.DB_CONFIG['database'],))
            columns = [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()

        self.assertEqual(columns, ['user_id', 'jadwal_id', 'tanggal'])

    def test_absensi_schema_supports_reason_and_sick_status(self):
        conn = database.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT COLUMN_NAME, COLUMN_TYPE
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME='absensi'
                  AND COLUMN_NAME IN ('alasan', 'status')
            """, (database.DB_CONFIG['database'],))
            columns = {name: column_type for name, column_type in cursor.fetchall()}
        finally:
            cursor.close()
            conn.close()

        self.assertIn('alasan', columns)
        self.assertIn("'sakit'", columns['status'])

    def test_admin_table_has_singleton_unique_constraint(self):
        conn = database.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME='admin'
                  AND COLUMN_NAME='singleton_key' AND NON_UNIQUE=0
            """, (database.DB_CONFIG['database'],))
            unique_count = cursor.fetchone()[0]
        finally:
            cursor.close()
            conn.close()

        self.assertGreaterEqual(unique_count, 1)


class SecurityConfigTests(unittest.TestCase):
    def test_flask_secret_key_is_not_public_default(self):
        self.assertNotEqual(
            app.app.secret_key, 'ganti_ini_dengan_kunci_rahasia_anda'
        )
        self.assertGreaterEqual(len(app.app.secret_key), 32)


# ══════════════════════════════════════════════════════════════════
# Checklist gap coverage — added by review 2026-08-26
# ══════════════════════════════════════════════════════════════════


class HealthEndpointTests(unittest.TestCase):
    """RT-HEALTH-01 / RT-HEALTH-02: /api/face/health trả trạng thái rõ."""

    def setUp(self):
        self.client = app.app.test_client()
        with self.client.session_transaction() as flask_session:
            flask_session['admin_id'] = 1

    @patch('face.recognition.get_engine_health')
    def test_health_returns_200_when_ready(self, get_health):
        """RT-HEALTH-01: ready=True → HTTP 200."""
        get_health.return_value = {
            'ready': True, 'gallery_ready': True,
            'gallery_templates': 5, 'gallery_users': 2,
            'threshold': 0.55, 'automatic_attendance_ready': True,
            'model': {'detector': 'det.onnx', 'recognizer': 'rec.onnx'},
        }
        response = self.client.get('/api/face/health')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['ready'])
        self.assertTrue(payload['automatic_attendance_ready'])

    @patch('face.recognition.get_engine_health')
    def test_health_returns_503_when_not_ready(self, get_health):
        """RT-HEALTH-02: model thiếu → HTTP 503 + ready=False."""
        get_health.return_value = {
            'ready': False, 'error': 'Khong tim thay ONNX',
            'gallery_ready': False, 'automatic_attendance_ready': False,
        }
        response = self.client.get('/api/face/health')
        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertFalse(payload['ready'])
        self.assertIn('error', payload)

    @patch.object(app, '_decode_frame', return_value=np.zeros((100, 100, 3), dtype=np.uint8))
    @patch('face.recognition.predict')
    def test_face_engine_error_returns_503_not_attendance(self, predict, _decode):
        """RT-HEALTH-02: FaceEngineError khi nhận diện → 503, không ghi."""
        from face.yolo_arcface import FaceEngineError
        predict.side_effect = FaceEngineError('Model ONNX thiếu')
        response = self.client.post('/api/absensi/proses', json={
            'frame': 'data:image/jpeg;base64,AAAA',
            'client_id': 'test_camera_01'
        })
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()['tipe'], 'model_unavailable')


class FailClosedCalibrationTests(unittest.TestCase):
    """RT-REC-03: Threshold=None → fail-closed, needs_calibration."""

    def setUp(self):
        app._consecutive_trackers.clear()

    @patch('face.recognition.predict')
    @patch('face.anti_spoofing.check_face')
    @patch.object(app.db, 'get_user_by_id')
    def test_null_threshold_returns_needs_calibration_and_no_attendance(
        self, get_user_by_id, spoofing_check, predict
    ):
        predict.return_value = [{
            'user_id': 1, 'confidence': 0.85, 'match_score': 0.85,
            'dikenali': False, 'recognition_status': 'needs_calibration',
            'bbox': (0, 0, 100, 100), 'track_id': 1,
            'detector_score': 0.95, 'quality_reason': None,
            'landmarks': [[30, 35], [70, 35], [50, 55], [35, 80], [65, 80]],
            'pipeline_latency_ms': 10.0,
            'detector_latency_ms': 5.0,
            'embedding_latency_ms': 3.0,
        }]
        spoofing_check.return_value = {
            'is_real': True, 'label': 'REAL', 'score': 1.0
        }
        get_user_by_id.return_value = {
            'id': 1, 'nama': 'Test', 'nim': '001',
            'kelas_id': 1, 'nama_kelas': 'ML-01'
        }

        with patch.object(app, 'RECOGNITION_REQUIRED_FRAMES', 1):
            result = app._proses_recognition(object(), tracker_key='calibration-test')

        # Phải trả needs_calibration, không ghi attendance
        has_calibration = any(
            item.get('tipe') == 'needs_calibration'
            for item in result.get('results', [result])
        )
        self.assertTrue(has_calibration)
        self.assertEqual(result['summary']['needs_calibration'], 1)
        self.assertEqual(result['summary']['recorded'], 0)


class DuplicateAttendanceTests(unittest.TestCase):
    """RT-ATT-01: Mỗi SV chỉ ghi 1 lần/buổi; duplicate trả trạng thái rõ."""

    def setUp(self):
        app._consecutive_trackers.clear()

    @patch.object(app, '_simpan_snapshot', return_value='snapshots/dup.jpg')
    @patch.object(app.db, 'get_statistik_dashboard', return_value={})
    @patch.object(app.db, 'catat_absensi')
    @patch.object(app.db, 'cek_sudah_absen')
    @patch.object(app.db, 'get_jadwal_aktif')
    @patch.object(app.db, 'get_user_by_id')
    @patch('face.anti_spoofing.check_face')
    @patch('face.recognition.predict')
    def test_already_attended_returns_duplikat_without_recording(
        self, predict, check_face, get_user_by_id, get_jadwal_aktif,
        cek_sudah_absen, catat_absensi, _get_stats, _save_snapshot
    ):
        predict.return_value = [{
            'user_id': 1, 'confidence': 35.0, 'match_score': 0.85,
            'dikenali': True, 'recognition_status': 'recognized',
            'bbox': (0, 0, 100, 100), 'track_id': 1,
            'detector_score': 0.95, 'quality_reason': None,
            'landmarks': [[30, 35], [70, 35], [50, 55], [35, 80], [65, 80]],
            'pipeline_latency_ms': 10.0,
            'detector_latency_ms': 5.0,
            'embedding_latency_ms': 3.0,
        }]
        check_face.return_value = {'is_real': True, 'label': 'REAL', 'score': 1.0}
        get_user_by_id.return_value = {
            'id': 1, 'nama': 'A', 'nim': '001', 'kelas_id': 9,
            'nama_kelas': 'ML-01'
        }
        get_jadwal_aktif.return_value = [{
            'id': 7, 'kelas_id': 9, 'nama_mk': 'Machine Learning',
            'batas_terlambat': '23:59:59'
        }]
        # Trả bản ghi đã điểm danh
        cek_sudah_absen.return_value = {'status': 'hadir', 'id': 99}

        with patch.object(app, 'RECOGNITION_REQUIRED_FRAMES', 1):
            result = app._proses_recognition(object(), tracker_key='dup-test')

        has_duplikat = any(
            item.get('tipe') == 'duplikat'
            for item in result.get('results', [result])
        )
        self.assertTrue(has_duplikat)
        catat_absensi.assert_not_called()


class ApiContractTests(unittest.TestCase):
    """RT-API-01: Schema per-face phải có đủ 7 trường bắt buộc."""

    REQUIRED_FIELDS = {
        'bbox', 'track_id', 'detector_score', 'match_score',
        'display_status', 'display_label', 'quality_reason',
    }

    def test_recognized_face_has_all_contract_fields(self):
        response = app._attach_face_metadata(
            {'status': 'ok', 'tipe': None, 'data': {'nama': 'Test'}},
            {
                'bbox': (10, 20, 80, 80), 'track_id': 3,
                'detector_score': 0.91, 'match_score': 0.78,
                'quality_reason': None, 'confidence': 0.78,
                'pipeline_latency_ms': 15.0,
            },
            0,
        )
        for field in self.REQUIRED_FIELDS:
            self.assertIn(field, response, f'Missing field: {field}')
        self.assertEqual(response['display_status'], 'recognized')

    def test_low_quality_face_has_all_contract_fields(self):
        response = app._attach_face_metadata(
            {'status': 'error', 'tipe': 'low_quality',
             'quality_reason': 'face_too_dark'},
            {
                'bbox': (10, 20, 80, 80), 'track_id': 5,
                'detector_score': 0.88, 'match_score': None,
                'quality_reason': 'face_too_dark', 'confidence': None,
                'pipeline_latency_ms': 12.0,
            },
            1,
        )
        for field in self.REQUIRED_FIELDS:
            self.assertIn(field, response, f'Missing field: {field}')
        self.assertEqual(response['display_status'], 'error')

    def test_verifying_face_has_warning_display_status(self):
        response = app._attach_face_metadata(
            {'status': 'skip', 'tipe': 'verifying'},
            {
                'bbox': (10, 20, 80, 80), 'track_id': 7,
                'detector_score': 0.92, 'match_score': 0.71,
                'quality_reason': None, 'confidence': 0.71,
                'pipeline_latency_ms': 8.0,
            },
            0,
        )
        for field in self.REQUIRED_FIELDS:
            self.assertIn(field, response, f'Missing field: {field}')
        self.assertEqual(response['display_status'], 'warning')

    def test_needs_calibration_face_has_warning_display_status(self):
        response = app._attach_face_metadata(
            {'status': 'skip', 'tipe': 'needs_calibration'},
            {
                'bbox': (10, 20, 80, 80), 'track_id': 9,
                'detector_score': 0.90, 'match_score': 0.65,
                'quality_reason': None, 'confidence': 0.65,
                'pipeline_latency_ms': 9.0,
            },
            0,
        )
        self.assertEqual(response['display_status'], 'warning')


class QualityDisplayLabelTests(unittest.TestCase):
    """RT-QLT-01: _attach_face_metadata gán đúng hướng dẫn cho từng quality_reason."""

    EXPECTED_LABELS = {
        'face_too_small': 'Lại gần máy ảnh hơn',
        'face_too_dark': 'Tăng ánh sáng khuôn mặt',
        'face_too_bright': 'Giảm ánh sáng gắt',
        'face_blurry': 'Giữ yên khuôn mặt',
        'landmarks_invalid': 'Nhìn thẳng vào máy ảnh',
        'face_out_of_box': 'Đặt trọn khuôn mặt vào khung',
        'face_out_of_frame': 'Đặt trọn khuôn mặt vào khung',
    }

    def test_each_quality_reason_maps_to_correct_display_label(self):
        for reason, expected_label in self.EXPECTED_LABELS.items():
            response = app._attach_face_metadata(
                {'status': 'error', 'tipe': 'low_quality',
                 'quality_reason': reason},
                {
                    'bbox': (0, 0, 80, 80), 'track_id': 1,
                    'detector_score': 0.9, 'match_score': None,
                    'quality_reason': reason, 'confidence': None,
                    'pipeline_latency_ms': 10.0,
                },
                0,
            )
            self.assertIn(expected_label, response['display_label'],
                          f'quality_reason={reason} should map to "{expected_label}"')


class LatencyFieldTests(unittest.TestCase):
    """RT-PERF-01: predict() trả đủ detector_latency_ms, embedding_latency_ms, pipeline_latency_ms."""

    @patch('face.recognition._load_gallery')
    @patch('face.recognition._load_engine')
    def test_predict_returns_all_latency_fields(self, load_engine, load_gallery):
        from face.yolo_arcface import FaceDetection, SpatialFaceTracker

        det = FaceDetection(
            (20, 20, 100, 100),
            np.asarray([
                [50, 55], [90, 55], [70, 75], [55, 100], [85, 100],
            ], dtype=np.float32),
            0.9,
        )
        mock_detector = Mock()
        mock_detector.detect.return_value = [det]

        mock_recognizer = Mock()
        mock_recognizer.embed.return_value = np.ones(128, dtype=np.float32) / np.sqrt(128)

        tracker = SpatialFaceTracker(iou_threshold=0.25, ttl_seconds=2)
        load_engine.return_value = (mock_detector, mock_recognizer, tracker)
        load_gallery.return_value = True

        gallery_ids = np.array([1])
        with patch.object(recognition, '_gallery_ids', gallery_ids), \
             patch.object(recognition, '_gallery_embeddings',
                          np.ones((1, 128), dtype=np.float32) / np.sqrt(128)), \
             patch.object(recognition, '_gallery_groups',
                          recognition._build_gallery_groups(gallery_ids)), \
             patch.object(recognition, '_gallery_group_source_id', id(gallery_ids)), \
             patch.object(recognition, 'FACE_MATCH_THRESHOLD', 0.5):
            image = np.full((200, 200, 3), 130, dtype=np.uint8)
            # Tạo ảnh có texture để vượt qua quality check
            for i in range(200):
                image[i, :, :] = max(45, min(220, i))
            results = recognition.predict(image)

        self.assertGreaterEqual(len(results), 1)
        for result in results:
            self.assertIn('detector_latency_ms', result)
            self.assertIn('embedding_latency_ms', result)
            self.assertIn('pipeline_latency_ms', result)
            self.assertIsInstance(result['detector_latency_ms'], float)
            self.assertIsInstance(result['embedding_latency_ms'], float)
            self.assertGreater(result['pipeline_latency_ms'], 0)

    @patch('face.recognition.evaluate_quality', return_value=None)
    @patch('face.recognition._load_gallery', return_value=True)
    @patch('face.recognition._load_engine')
    def test_completed_track_reuses_pinned_identity_without_embedding(
        self, load_engine, _load_gallery, _quality
    ):
        from face.yolo_arcface import FaceDetection, SpatialFaceTracker

        det = FaceDetection(
            (20, 20, 100, 100),
            np.asarray([
                [50, 55], [90, 55], [70, 75], [55, 100], [85, 100],
            ], dtype=np.float32),
            0.9,
        )
        mock_detector = Mock()
        mock_detector.detect.return_value = [det]
        mock_recognizer = Mock()
        mock_recognizer.embed.return_value = np.ones(128, dtype=np.float32) / np.sqrt(128)

        tracker = SpatialFaceTracker(iou_threshold=0.25, ttl_seconds=2)
        load_engine.return_value = (mock_detector, mock_recognizer, tracker)
        image = np.full((200, 200, 3), 130, dtype=np.uint8)
        for i in range(200):
            image[i, :, :] = max(45, min(220, i))

        with patch.object(recognition, '_gallery_ids', np.array([1])), \
             patch.object(recognition, '_gallery_embeddings',
                          np.ones((1, 128), dtype=np.float32) / np.sqrt(128)), \
             patch.object(recognition, 'FACE_MATCH_THRESHOLD', 0.5):
            first = recognition.predict(image, tracker_key='pin-camera')[0]
            marked = recognition.mark_track_completed(
                'pin-camera', first['track_id'], first['user_id'],
                confidence=first['confidence'], match_score=first['match_score']
            )
            second = recognition.predict(image, tracker_key='pin-camera')[0]

        self.assertTrue(marked)
        self.assertTrue(second.get('completed_track'))
        self.assertEqual(second['user_id'], 1)
        mock_recognizer.embed.assert_called_once()


class TrainerRejectionTests(unittest.TestCase):
    """RT-REG-01: trainer.py từ chối ảnh 0 mặt / >1 mặt / chất lượng thấp."""

    @patch('face.trainer.reload_model')
    @patch('face.trainer._atomic_json_dump')
    @patch('face.trainer._atomic_npz_dump')
    @patch('face.trainer._faces_from_frame')
    @patch('face.trainer.cv2.imread')
    @patch('face.trainer.os.listdir')
    @patch('face.trainer.os.path.isdir', return_value=True)
    @patch('face.trainer.DATASET_PATH', '/fake/dataset')
    def test_images_with_zero_or_multiple_faces_are_rejected(
        self, _isdir, listdir, imread, faces_from_frame,
        npz_dump, json_dump, _reload
    ):
        from face import trainer

        # Giả lập: thư mục user "1" có 3 ảnh
        def mock_listdir(path):
            if path == '/fake/dataset':
                return ['1']
            return ['good.jpg', 'noface.jpg', 'multi.jpg']

        listdir.side_effect = mock_listdir
        imread.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

        # good.jpg → 1 mặt, noface.jpg → 0 mặt, multi.jpg → 2 mặt
        good_face = SimpleNamespace(
            normed_embedding=np.ones(128, dtype=np.float32) / np.sqrt(128)
        )
        faces_from_frame.side_effect = [
            [good_face],  # good.jpg → 1 mặt
            [],           # noface.jpg → 0 mặt
            [good_face, good_face],  # multi.jpg → 2 mặt
        ]

        result = trainer.train_model()

        self.assertTrue(result)
        # Kiểm tra diagnostics ghi nhận 1 accepted, 2 rejected
        json_call_args = json_dump.call_args[0]
        diagnostics = json_call_args[1]
        self.assertEqual(diagnostics['accepted_total'], 1)
        self.assertEqual(diagnostics['rejected_total'], 2)
        rejected = diagnostics['users']['1']['rejected']
        reasons = [item['reason'] for item in rejected]
        self.assertIn('face_count_0', reasons)
        self.assertIn('face_count_2', reasons)


class RealtimeGapFixTests(unittest.TestCase):
    def setUp(self):
        app._consecutive_trackers.clear()
        app._completed_trackers.clear()
        self.frame = np.zeros((100, 100, 3), dtype=np.uint8)

    @patch.object(app.db, 'catat_absensi')
    @patch.object(app.db, 'cek_sudah_absen', return_value=None)
    @patch.object(app.db, 'get_jadwal_aktif')
    @patch.object(app.db, 'get_user_by_id')
    @patch('face.anti_spoofing.check_face')
    @patch('face.recognition.predict')
    def test_multiple_active_schedules_block_attendance(
        self, predict, check_face, get_user_by_id, get_jadwal_aktif,
        cek_sudah_absen, catat_absensi
    ):
        predict.return_value = [{
            'user_id': 1, 'track_id': 11, 'confidence': 0.9,
            'dikenali': True, 'bbox': (0, 0, 80, 80)
        }]
        check_face.return_value = {'is_real': True, 'label': 'REAL', 'score': 1.0}
        get_user_by_id.return_value = {
            'id': 1, 'nama': 'A', 'nim': '001', 'kelas_id': 9,
            'nama_kelas': 'ML-01'
        }
        get_jadwal_aktif.return_value = [
            {'id': 7, 'kelas_id': 9, 'nama_mk': 'ML A', 'batas_terlambat': '23:59:59'},
            {'id': 8, 'kelas_id': 9, 'nama_mk': 'ML B', 'batas_terlambat': '23:59:59'},
        ]

        with patch.object(app, 'RECOGNITION_REQUIRED_FRAMES', 1):
            result = app._proses_recognition(self.frame, tracker_key='gap-schedule')

        self.assertEqual(result['tipe'], 'multiple_active_schedules')
        self.assertEqual(result['summary']['multiple_active_schedules'], 1)
        cek_sudah_absen.assert_not_called()
        catat_absensi.assert_not_called()

    @patch.object(app.db, 'get_jadwal_aktif', side_effect=database.DatabaseQueryError('down'))
    @patch('face.anti_spoofing.check_face')
    @patch('face.recognition.predict')
    def test_database_outage_is_not_reported_as_no_schedule(
        self, predict, check_face, _get_jadwal_aktif
    ):
        predict.return_value = [{
            'user_id': 1, 'track_id': 11, 'confidence': 0.9,
            'dikenali': True, 'bbox': (0, 0, 80, 80)
        }]
        check_face.return_value = {'is_real': True, 'label': 'REAL', 'score': 1.0}

        with patch.object(app, 'RECOGNITION_REQUIRED_FRAMES', 1):
            result = app._proses_recognition(self.frame, tracker_key='gap-db')

        self.assertEqual(result['tipe'], 'database_unavailable')
        self.assertEqual(result['summary']['database_unavailable'], 1)

    @patch.object(app, '_simpan_snapshot', return_value='snapshots/a.jpg')
    @patch.object(app.db, 'get_statistik_dashboard', return_value={})
    @patch.object(app.db, 'catat_absensi', return_value=101)
    @patch.object(app.db, 'cek_sudah_absen', return_value=None)
    @patch.object(app.db, 'get_jadwal_aktif')
    @patch.object(app.db, 'get_user_by_id')
    @patch('face.anti_spoofing.check_face')
    @patch('face.recognition.predict')
    def test_completed_track_does_not_repeat_liveness_or_db(
        self, predict, check_face, get_user_by_id, get_jadwal_aktif,
        cek_sudah_absen, catat_absensi, _get_stats, _save_snapshot
    ):
        predict.return_value = [{
            'user_id': 1, 'track_id': 11, 'confidence': 0.9,
            'dikenali': True, 'bbox': (0, 0, 80, 80)
        }]
        check_face.return_value = {'is_real': True, 'label': 'REAL', 'score': 1.0}
        get_user_by_id.return_value = {
            'id': 1, 'nama': 'A', 'nim': '001', 'kelas_id': 9,
            'nama_kelas': 'ML-01'
        }
        get_jadwal_aktif.return_value = [{
            'id': 7, 'kelas_id': 9, 'nama_mk': 'Machine Learning',
            'batas_terlambat': '23:59:59'
        }]

        with patch.object(app, 'RECOGNITION_REQUIRED_FRAMES', 1):
            first = app._proses_recognition(self.frame, tracker_key='gap-terminal')
            second = app._proses_recognition(self.frame, tracker_key='gap-terminal')

        self.assertEqual(first['status'], 'ok')
        self.assertEqual(second['tipe'], 'duplikat')
        self.assertTrue(second.get('cached'))
        check_face.assert_called_once()
        get_user_by_id.assert_called_once()
        cek_sudah_absen.assert_called_once()
        catat_absensi.assert_called_once()

    @patch.object(app, '_start_gallery_rebuild_background', return_value=True)
    @patch.object(app.db, 'hapus_user', return_value=True)
    @patch.object(app.db, 'get_user_by_id', return_value={'id': 1})
    def test_student_delete_triggers_gallery_rebuild(
        self, _get_user, _hapus_user, rebuild
    ):
        client = app.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session['admin_id'] = 1

        response = client.post('/mahasiswa/hapus/1')

        self.assertEqual(response.status_code, 302)
        rebuild.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
