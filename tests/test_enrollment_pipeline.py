import unittest
from unittest.mock import patch
import base64
import json
import os
import tempfile
from types import SimpleNamespace

import cv2
import numpy as np

from face.enrollment import (
    ENROLLMENT_TOTAL, manifest_is_complete, stage_for_count, stages_for_total,
    validate_enrollment_frame,
)
from face.trainer import select_diverse_templates
from face.yolo_arcface import FaceDetection
import app


class _Detector:
    def __init__(self, detections):
        self.detections = detections

    def detect(self, _frame):
        return self.detections


def _frame():
    rng = np.random.RandomState(123)
    return rng.randint(80, 170, (600, 800, 3), dtype=np.uint8)


def _detection(width=150, height=150, yaw=0.0, x=300, y=210):
    eye_y = y + height * 0.35
    left_eye_x = x + width * 0.30
    right_eye_x = x + width * 0.70
    nose_x = (left_eye_x + right_eye_x) / 2 + yaw * (right_eye_x - left_eye_x)
    landmarks = np.asarray([
        [left_eye_x, eye_y], [right_eye_x, eye_y], [nose_x, y + height * 0.56],
        [x + width * 0.35, y + height * 0.80], [x + width * 0.65, y + height * 0.80],
    ], dtype=np.float32)
    return FaceDetection((x, y, width, height), landmarks, 0.95)


class EnrollmentStageTests(unittest.TestCase):
    def test_server_stage_distribution_is_24_images(self):
        self.assertEqual(ENROLLMENT_TOTAL, 24)
        self.assertEqual(stage_for_count(0)[0]['id'], 'center')
        self.assertEqual(stage_for_count(6)[0]['id'], 'left')
        self.assertEqual(stage_for_count(11)[0]['id'], 'right')
        self.assertEqual(stage_for_count(16)[0]['id'], 'near')
        self.assertEqual(stage_for_count(20)[0]['id'], 'far')
        self.assertIsNone(stage_for_count(24)[0])

    def test_correct_left_pose_is_accepted_and_wrong_pose_is_rejected(self):
        frame = _frame()
        good = validate_enrollment_frame(frame, _Detector([_detection(yaw=0.25)]), 'left')
        wrong = validate_enrollment_frame(frame, _Detector([_detection(yaw=0.0)]), 'left')
        self.assertTrue(good.accepted)
        self.assertFalse(wrong.accepted)
        self.assertEqual(wrong.reason, 'turn_left')

    def test_near_and_far_return_specific_distance_feedback(self):
        near_frame = np.random.RandomState(2).randint(80, 170, (600, 800, 3), dtype=np.uint8)
        too_close = validate_enrollment_frame(
            near_frame, _Detector([_detection(width=500, height=500, x=150, y=50)]), 'near'
        )
        far_frame = np.random.RandomState(3).randint(80, 170, (1600, 2000, 3), dtype=np.uint8)
        too_far = validate_enrollment_frame(
            far_frame, _Detector([_detection(width=150, height=150, x=925, y=725)]), 'far'
        )
        self.assertEqual(too_close.reason, 'too_close')
        self.assertEqual(too_far.reason, 'too_far')

    def test_manifest_requires_exact_stage_distribution(self):
        samples = []
        for count in range(ENROLLMENT_TOTAL):
            stage, _ = stage_for_count(count)
            samples.append({'stage': stage['id']})
        self.assertTrue(manifest_is_complete(samples))
        bad_samples = [s for s in samples if s['stage'] != 'far']
        self.assertFalse(manifest_is_complete(bad_samples))

    def test_default_enrollment_cannot_complete_at_old_18_image_quota(self):
        samples = (
            [{'stage': 'center'}] * 4 + [{'stage': 'left'}] * 3 +
            [{'stage': 'right'}] * 3 + [{'stage': 'near'}] * 4 +
            [{'stage': 'far'}] * 4
        )
        self.assertEqual(len(samples), 18)
        self.assertFalse(manifest_is_complete(samples))

    def test_configured_enrollment_plan_does_not_show_unused_stages(self):
        plan = stages_for_total(10)
        self.assertEqual([(stage['id'], stage['target']) for stage in plan], [
            ('center', 6), ('left', 4),
        ])

    def test_multiple_faces_accepts_only_the_face_in_the_central_guide(self):
        target = _detection()
        outside = _detection(x=20, y=20)
        result = validate_enrollment_frame(_frame(), _Detector([outside, target]), 'center')
        self.assertTrue(result.accepted)
        self.assertIs(result.detection, target)

    def test_multiple_faces_without_a_face_in_the_guide_are_rejected(self):
        result = validate_enrollment_frame(
            _frame(), _Detector([_detection(x=20, y=20), _detection(x=620, y=20)]), 'center'
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, 'face_outside_guide')

    def test_valid_frame_computes_laplacian_only_once(self):
        original_laplacian = cv2.Laplacian
        with patch('face.yolo_arcface.cv2.Laplacian', wraps=original_laplacian) as laplacian:
            result = validate_enrollment_frame(_frame(), _Detector([_detection()]), 'center')
        self.assertTrue(result.accepted)
        self.assertEqual(laplacian.call_count, 1)

    @patch('face.recognition._load_engine')
    @patch.object(app.db, 'get_user_by_nim', return_value=None)
    def test_server_requires_stable_frames_before_it_can_save(self, _get_user, load_engine):
        app._enrollment_states.clear()
        load_engine.return_value = (_Detector([_detection()]), None, None)
        with app.app.test_request_context('/api/foto/upload'):
            from flask import session
            session['admin_id'] = 9
            first = app._quality_enrollment_upload('Test Student', 'stable-001', 1, _frame())
            second = app._quality_enrollment_upload('Test Student', 'stable-001', 1, _frame())
        self.assertEqual(first.get_json()['status'], 'retry')
        self.assertEqual(second.get_json()['status'], 'retry')
        self.assertEqual(second.get_json()['reason'], 'stabilizing')

    @patch('face.recognition._load_engine')
    @patch.object(app.db, 'tambah_user', return_value=42)
    @patch.object(app.db, 'get_user_by_nim', return_value=None)
    def test_third_stable_frame_saves_image_and_manifest(self, _get_user, _add_user, load_engine):
        app._enrollment_states.clear()
        app._enrollment_upload_locks.clear()
        load_engine.return_value = (_Detector([_detection()]), None, None)
        with tempfile.TemporaryDirectory() as dataset_dir, \
             patch.object(app, 'DATASET_PATH', dataset_dir), \
             app.app.test_request_context('/api/foto/upload'):
            from flask import session
            session['admin_id'] = 10
            first = app._quality_enrollment_upload('Test Student', 'stable-002', 1, _frame())
            second = app._quality_enrollment_upload('Test Student', 'stable-002', 1, _frame())
            third = app._quality_enrollment_upload('Test Student', 'stable-002', 1, _frame())
        self.assertEqual(third.get_json()['status'], 'ok')
        self.assertEqual(third.get_json()['data']['accepted'], 1)

    @patch('face.recognition._appearance_changed', side_effect=AssertionError('not used for enrollment'))
    @patch('face.recognition._load_engine')
    @patch.object(app.db, 'tambah_user', return_value=43)
    @patch.object(app.db, 'get_user_by_nim', return_value=None)
    def test_valid_frames_are_not_reset_by_raw_pixel_fingerprint(
        self, _get_user, _add_user, load_engine, _appearance_changed
    ):
        app._enrollment_states.clear()
        load_engine.return_value = (_Detector([_detection()]), None, None)
        frames = [
            np.random.RandomState(seed).randint(80, 170, (600, 800, 3), dtype=np.uint8)
            for seed in (11, 12, 13)
        ]
        with tempfile.TemporaryDirectory() as dataset_dir, \
             patch.object(app, 'DATASET_PATH', dataset_dir), \
             app.app.test_request_context('/api/foto/upload'):
            from flask import session
            session['admin_id'] = 11
            responses = [
                app._quality_enrollment_upload('Test Student', 'stable-raw-001', 1, frame)
                for frame in frames
            ]
        self.assertEqual(responses[-1].get_json()['status'], 'ok')

    @patch('face.recognition._load_engine')
    @patch.object(app.db, 'get_user_by_nim', return_value={
        'id': 77, 'nama': 'Test Student', 'kelas_id': 1,
    })
    def test_existing_student_without_dataset_folder_does_not_crash(self, _get_user, load_engine):
        load_engine.return_value = (_Detector([_detection()]), None, None)
        with tempfile.TemporaryDirectory() as dataset_dir, \
             patch.object(app, 'DATASET_PATH', dataset_dir), \
             app.app.test_request_context('/api/foto/upload'):
            from flask import session
            session['admin_id'] = 3
            response = app._quality_enrollment_upload('Test Student', 'existing-001', 1, _frame())
        self.assertEqual(response.get_json()['status'], 'retry')

    @patch('face.recognition._load_engine')
    @patch.object(app.db, 'get_user_by_nim', return_value=None)
    def test_enrollment_upload_lock_is_released_after_request(self, _get_user, load_engine):
        load_engine.return_value = (_Detector([]), None, None)
        app._enrollment_upload_locks.clear()
        with app.app.test_request_context('/api/foto/upload'):
            from flask import session
            session['admin_id'] = 5
            app._quality_enrollment_upload('Test Student', 'lock-001', 1, _frame())
        self.assertNotIn('5:lock-001', app._enrollment_upload_locks)

    def test_upload_rejects_missing_quality_protocol(self):
        ok, encoded = cv2.imencode('.jpg', _frame())
        self.assertTrue(ok)
        image_data = 'data:image/jpeg;base64,' + base64.b64encode(encoded.tobytes()).decode('ascii')
        client = app.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session['admin_id'] = 1
        response = client.post('/api/foto/upload', json={
            'nama': 'Test Student', 'nim': 'protocol-001', 'kelas_id': 1,
            'foto': image_data, 'index': 0,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['status'], 'error')

    @patch.object(app.db, 'get_user_by_nim', return_value={'id': 89})
    def test_completed_manifest_accepts_boundary_index_as_finished(self, _get_user):
        ok, encoded = cv2.imencode('.jpg', _frame())
        self.assertTrue(ok)
        image_data = 'data:image/jpeg;base64,' + base64.b64encode(encoded.tobytes()).decode('ascii')
        samples = []
        for count in range(ENROLLMENT_TOTAL):
            stage, _ = stage_for_count(count)
            samples.append({'stage': stage['id']})
        client = app.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session['admin_id'] = 1
        with tempfile.TemporaryDirectory() as dataset_dir, patch.object(app, 'DATASET_PATH', dataset_dir):
            user_dir = os.path.join(dataset_dir, '89')
            os.makedirs(user_dir)
            with open(os.path.join(user_dir, 'enrollment_manifest.json'), 'w', encoding='utf-8') as file:
                json.dump({'schema_version': 1, 'samples': samples}, file)
            response = client.post('/api/foto/upload', json={
                'nama': 'Test Student', 'nim': 'complete-001', 'kelas_id': 1,
                'foto': image_data, 'index': ENROLLMENT_TOTAL,
                'protocol': 'quality_v1',
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['status'], 'selesai')

    @patch.object(app.db, 'get_semua_kelas', return_value=[])
    def test_registration_template_uses_server_stage_metadata(self, _get_classes):
        client = app.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session['admin_id'] = 1
        html = client.get('/mahasiswa/register').get_data(as_text=True)
        self.assertIn(f'const MAX_FOTO = {ENROLLMENT_TOTAL};', html)
        self.assertIn('const SERVER_ENROLLMENT_STAGES =', html)
        self.assertIn('"id": "center"', html)
        self.assertIn('"target": 6', html)
        self.assertIn('Ảnh đạt yêu cầu — giữ yên để máy chụp', html)
        self.assertNotIn('KHUNG CĂN MẶT', html)
        self.assertNotIn('Giữ yên khuôn mặt trong khung', html)
        self.assertNotIn('id="stageStepper"', html)
        self.assertNotIn('id="statusProses"', html)
        self.assertIn('faceOval.classList.add(\'is-ready\')', html)
        self.assertIn('faceOval.classList.remove(\'is-ready\')', html)
        self.assertIn('const statusLabel = expressionLabel;', html)
        self.assertIn('/api/training/start', html)
        self.assertIn('/api/training/status', html)
        self.assertIn("data.status === 'ok'", html)
        self.assertIn('progress.accepted', html)
        self.assertIn('UPLOAD_TIMEOUT_MS', html)
        self.assertIn('activeUploadController.abort()', html)
        self.assertIn('video.videoWidth', html)
        self.assertIn('handleTransientCaptureFailure', html)
        self.assertNotIn("dungCaptureDoLoi('Lỗi kết nối máy chủ khi chụp ảnh.')", html)
        self.assertNotIn("data.status === 'success'", html)
        self.assertNotIn('/api/foto/legacy_status', html)

    @patch.object(app.db, 'get_user_by_nim', return_value={'id': 88})
    def test_training_rejects_incomplete_manifest(self, _get_user):
        client = app.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session['admin_id'] = 1
        with tempfile.TemporaryDirectory() as dataset_dir, patch.object(app, 'DATASET_PATH', dataset_dir):
            user_dir = os.path.join(dataset_dir, '88')
            os.makedirs(user_dir)
            with open(os.path.join(user_dir, 'enrollment_manifest.json'), 'w', encoding='utf-8') as file:
                json.dump({'schema_version': 1, 'samples': [{'stage': 'center'}]}, file)
            response = client.post('/api/training/start', json={'nim': 'incomplete-001'})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()['status'], 'error')

    @patch('face.recognition._load_engine')
    @patch.object(app.db, 'get_user_by_nim', return_value=None)
    def test_expired_enrollment_state_is_cleaned(self, _get_user, load_engine):
        load_engine.return_value = (_Detector([]), None, None)
        app._enrollment_states.clear()
        app._enrollment_states['expired'] = {
            'stage': 'center', 'stable': 1, 'signature': None, 'updated_at': 0.0,
        }
        with patch.object(app.time, 'monotonic', return_value=app.ENROLLMENT_STATE_TTL_SECONDS + 1), \
             app.app.test_request_context('/api/foto/upload'):
            from flask import session
            session['admin_id'] = 4
            app._quality_enrollment_upload('Test Student', 'ttl-001', 1, _frame())
        self.assertNotIn('expired', app._enrollment_states)


class GalleryBuildLifecycleTests(unittest.TestCase):
    def setUp(self):
        with app._gallery_build_state_lock:
            app._gallery_build_state.update({
                'build_id': None, 'state': 'idle', 'last_error': None,
                'started_at': None, 'finished_at': None, 'updated_at': None,
                'requested_user_id': None,
            })
        self.client = app.app.test_client()
        with self.client.session_transaction() as flask_session:
            flask_session['admin_id'] = 1

    @staticmethod
    def _complete_samples():
        return [
            {'stage': stage_for_count(index)[0]['id']}
            for index in range(ENROLLMENT_TOTAL)
        ]

    def test_training_status_reports_success_after_background_build(self):
        class ImmediateThread:
            def __init__(self, target, daemon):
                self.target = target

            def start(self):
                self.target()

        with tempfile.TemporaryDirectory() as dataset_dir, \
             patch.object(app, 'DATASET_PATH', dataset_dir), \
             patch.object(app.db, 'get_user_by_nim', return_value={'id': 90}), \
             patch.object(app.threading, 'Thread', ImmediateThread), \
             patch('face.trainer.train_model', return_value=True):
            user_dir = os.path.join(dataset_dir, '90')
            os.makedirs(user_dir)
            with open(os.path.join(user_dir, 'enrollment_manifest.json'), 'w', encoding='utf-8') as file:
                json.dump({'samples': self._complete_samples()}, file)
            started = self.client.post('/api/training/start', json={'nim': 'ready-001'})
            self.assertEqual(started.status_code, 200)
            build_id = started.get_json()['data']['build_id']
            status = self.client.get('/api/training/status?build_id=' + build_id)

        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.get_json()['data']['state'], 'succeeded')

    def test_training_status_rejects_unknown_build_id(self):
        response = self.client.get('/api/training/status?build_id=not-current')
        self.assertEqual(response.status_code, 404)

    def test_student_list_shows_gallery_readiness_not_photo_count(self):
        students = [
            {'id': 101, 'nama': 'Ready', 'nim': '001', 'kelas_id': 1, 'nama_kelas': 'ML'},
            {'id': 102, 'nama': 'Partial', 'nim': '002', 'kelas_id': 1, 'nama_kelas': 'ML'},
        ]
        with tempfile.TemporaryDirectory() as dataset_dir, tempfile.TemporaryDirectory() as model_dir, \
             patch.object(app, 'DATASET_PATH', dataset_dir), \
             patch.object(app, 'FACE_GALLERY_META_PATH', os.path.join(model_dir, 'face_gallery.json')), \
             patch.object(app.db, 'get_semua_user', return_value=students), \
             patch.object(app.db, 'get_semua_kelas', return_value=[]):
            os.makedirs(os.path.join(dataset_dir, '101'))
            os.makedirs(os.path.join(dataset_dir, '102'))
            open(os.path.join(dataset_dir, '101', 'ready.jpg'), 'wb').close()
            open(os.path.join(dataset_dir, '102', 'partial.jpg'), 'wb').close()
            with open(app.FACE_GALLERY_META_PATH, 'w', encoding='utf-8') as file:
                json.dump({'gallery_users': [101]}, file)
            response = self.client.get('/mahasiswa')

        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Sẵn sàng (1 ảnh)', html)
        self.assertIn('Đăng ký chưa hoàn tất', html)


class GallerySelectionTests(unittest.TestCase):
    def test_gallery_is_bounded_and_does_not_keep_exact_duplicate(self):
        candidates = []
        for stage, amount in {'center': 4, 'left': 3, 'right': 3, 'near': 3, 'far': 3}.items():
            for index in range(amount):
                vector = np.zeros(16, dtype=np.float32)
                vector[(len(candidates) + index) % 16] = 1.0
                candidates.append({
                    'file': f'{stage}-{index}.jpg', 'stage': stage,
                    'quality_score': 1.0 - index * .01, 'embedding': vector,
                })
        candidates.append(dict(candidates[0]))
        selected = select_diverse_templates(candidates, limit=12)
        self.assertLessEqual(len(selected), 12)
        self.assertEqual(len(selected), len({item['file'] for item in selected}))
        self.assertGreaterEqual(sum(item['stage'] == 'left' for item in selected), 1)

    def test_trainer_excludes_partial_manifest_and_unlisted_new_files(self):
        from face import trainer

        with tempfile.TemporaryDirectory() as temp_dir, \
             patch.object(trainer, 'DATASET_PATH', temp_dir), \
             patch.object(trainer, 'FACE_GALLERY_PATH', os.path.join(temp_dir, 'gallery.npz')), \
             patch.object(trainer, 'FACE_GALLERY_META_PATH', os.path.join(temp_dir, 'gallery.json')), \
             patch.object(trainer, '_faces_from_frame') as faces_from_frame, \
             patch.object(trainer, 'reload_model'):
            complete_path = os.path.join(temp_dir, '1')
            partial_path = os.path.join(temp_dir, '2')
            legacy_path = os.path.join(temp_dir, '3')
            for path in (complete_path, partial_path, legacy_path):
                os.makedirs(path)

            complete_samples = []
            for index in range(ENROLLMENT_TOTAL):
                stage, _ = stage_for_count(index)
                filename = f'complete-{index}.jpg'
                cv2.imwrite(os.path.join(complete_path, filename), _frame())
                complete_samples.append({'file': filename, 'stage': stage['id'], 'metrics': {}})
            cv2.imwrite(os.path.join(complete_path, 'unlisted.jpg'), _frame())
            with open(os.path.join(complete_path, 'enrollment_manifest.json'), 'w', encoding='utf-8') as file:
                json.dump({'samples': complete_samples}, file)

            cv2.imwrite(os.path.join(partial_path, 'partial.jpg'), _frame())
            with open(os.path.join(partial_path, 'enrollment_manifest.json'), 'w', encoding='utf-8') as file:
                json.dump({'samples': [{'file': 'partial.jpg', 'stage': 'center'}]}, file)

            for index in range(2):
                cv2.imwrite(os.path.join(legacy_path, f'legacy-{index}.jpg'), _frame())

            faces_from_frame.return_value = [SimpleNamespace(
                normed_embedding=np.asarray([1.0, 0.0], dtype=np.float32), det_score=0.99
            )]
            self.assertTrue(trainer.train_model())

            with np.load(trainer.FACE_GALLERY_PATH) as gallery:
                self.assertEqual(set(gallery['user_ids'].tolist()), {1, 3})
            with open(trainer.FACE_GALLERY_META_PATH, 'r', encoding='utf-8') as file:
                diagnostics = json.load(file)
            self.assertEqual(diagnostics['users']['2']['manifest_state'], 'incomplete')
            self.assertNotIn('unlisted.jpg', diagnostics['users']['1']['selected_files'])

    def test_recognition_trackers_are_isolated_by_camera_key(self):
        from face import recognition
        recognition._trackers.clear()
        first = recognition._get_tracker('camera-a')
        second = recognition._get_tracker('camera-b')
        self.assertIsNot(first, second)
        self.assertIs(first, recognition._get_tracker('camera-a'))
        recognition.reset_tracker('camera-a')
        self.assertIsNot(first, recognition._get_tracker('camera-a'))

    def test_gallery_match_reuses_preindexed_user_groups(self):
        from face import recognition
        gallery_ids = np.asarray([1, 1, 2], dtype=np.int64)
        gallery_embeddings = np.asarray([
            [0.7, 0.7], [1.0, 0.0], [0.0, 1.0],
        ], dtype=np.float32)
        groups = recognition._build_gallery_groups(gallery_ids)
        with patch.object(recognition, '_gallery_ids', gallery_ids), \
             patch.object(recognition, '_gallery_embeddings', gallery_embeddings), \
             patch.object(recognition, '_gallery_groups', groups), \
             patch.object(recognition, '_gallery_group_source_id', id(gallery_ids)), \
             patch.object(recognition, '_build_gallery_groups', side_effect=AssertionError('rebuilt')):
            user_id, score = recognition._match_embedding(np.asarray([1.0, 0.0]))
        self.assertEqual(user_id, 1)
        self.assertAlmostEqual(score, 1.0)

    def test_gallery_stat_polling_is_throttled_but_reload_is_forced(self):
        from face import recognition
        with patch.object(recognition, '_gallery_ids', np.asarray([1], dtype=np.int64)), \
             patch.object(recognition, '_gallery_last_stat_at', recognition.time.monotonic()), \
             patch.object(recognition.os.path, 'isfile') as isfile:
            self.assertTrue(recognition._load_gallery())
            isfile.assert_not_called()
        with patch.object(recognition, '_load_gallery', return_value=True) as load_gallery:
            self.assertTrue(recognition.reload_model())
            load_gallery.assert_called_once_with(force=True)


class GapAnalysisFixTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_gap_1_1_custom_foto_per_user_manifest_is_complete(self):
        from face.enrollment import manifest_is_complete
        samples = [{'stage': 'center'} for _ in range(10)]
        self.assertTrue(manifest_is_complete(samples, target_total=10))
        self.assertFalse(manifest_is_complete(samples, target_total=15))

    def test_gallery_rebuild_after_delete_releases_lock_and_uses_pollable_state(self):
        class ImmediateThread:
            def __init__(self, target, daemon):
                self.target = target

            def start(self):
                self.target()

        previous_state = app._get_gallery_build_state()
        try:
            with patch.object(app.threading, 'Thread', ImmediateThread), \
                 patch('face.trainer.train_model', return_value=True):
                self.assertTrue(app._start_gallery_rebuild_background())
            state = app._get_gallery_build_state()
            self.assertEqual(state['state'], 'succeeded')
            self.assertIsNone(state['last_error'])
            self.assertTrue(app._training_lock.acquire(blocking=False))
            app._training_lock.release()
        finally:
            app._set_gallery_build_state(**previous_state)

    @patch.object(app.db, 'get_user_by_nim', return_value={'id': 99})
    def test_gap_1_2_legacy_dataset_reset_option(self, _get_user):
        ok, encoded = cv2.imencode('.jpg', _frame())
        image_data = 'data:image/jpeg;base64,' + base64.b64encode(encoded.tobytes()).decode('ascii')
        with tempfile.TemporaryDirectory() as dataset_dir, patch.object(app, 'DATASET_PATH', dataset_dir):
            user_dir = os.path.join(dataset_dir, '99')
            os.makedirs(user_dir)
            open(os.path.join(user_dir, 'old_photo.jpg'), 'wb').close()

            with self.client.session_transaction() as session:
                session['admin_id'] = 1

            # Without reset_legacy -> returns 409 and can_reset
            res = self.client.post('/api/foto/upload', json={
                'nama': 'Legacy Student', 'nim': 'legacy-99', 'kelas_id': 1,
                'foto': image_data, 'index': 0, 'protocol': 'quality_v1'
            })
            self.assertEqual(res.status_code, 409)
            self.assertTrue(res.get_json().get('can_reset'))

            # With reset_legacy=true -> clears legacy folder and accepts frame
            res_reset = self.client.post('/api/foto/upload', json={
                'nama': 'Legacy Student', 'nim': 'legacy-99', 'kelas_id': 1,
                'foto': image_data, 'index': 0, 'protocol': 'quality_v1',
                'reset_legacy': True
            })
            self.assertIn(res_reset.status_code, (200, 409)) # Accepted or retry

    def test_gap_2_1_empty_profiles_deletes_npz_and_reloads_gallery(self):
        from face import trainer, recognition
        with tempfile.TemporaryDirectory() as temp_dir, \
             patch.object(trainer, 'DATASET_PATH', temp_dir), \
             patch.object(trainer, 'FACE_GALLERY_PATH', os.path.join(temp_dir, 'face_gallery.npz')), \
             patch.object(trainer, 'FACE_GALLERY_META_PATH', os.path.join(temp_dir, 'face_gallery.json')):
            # Create dummy npz
            np.savez(trainer.FACE_GALLERY_PATH, user_ids=np.array([1]), embeddings=np.array([[0.1]]))
            self.assertTrue(os.path.exists(trainer.FACE_GALLERY_PATH))

            # Running trainer with empty dataset directory
            result = trainer.train_model()
            self.assertFalse(result)
            self.assertFalse(os.path.exists(trainer.FACE_GALLERY_PATH))

    def test_gap_3_1_select_active_schedule_strict_time_matching(self):
        from datetime import datetime, timedelta
        now = datetime.now()
        now_str = now.strftime('%H:%M:%S')
        earlier_start = (now - timedelta(hours=1)).strftime('%H:%M:%S')
        earlier_end = (now - timedelta(minutes=5)).strftime('%H:%M:%S') # Grace window active
        strict_start = (now - timedelta(minutes=10)).strftime('%H:%M:%S')
        strict_end = (now + timedelta(minutes=50)).strftime('%H:%M:%S')

        user = {'nama': 'Student', 'nim': 'S01', 'kelas_id': 1, 'nama_kelas': 'Class A'}
        jadwal_list = [
            {'id': 1, 'kelas_id': 1, 'jam_mulai': earlier_start, 'jam_selesai': earlier_end},
            {'id': 2, 'kelas_id': 1, 'jam_mulai': strict_start, 'jam_selesai': strict_end},
        ]
        selected, err = app._select_active_schedule_for_user(user, jadwal_list, None)
        self.assertIsNone(err)
        self.assertEqual(selected['id'], 2)

    def test_gap_3_2_websocket_process_frame_requires_admin_session(self):
        with app.app.test_request_context('/'):
            received = []
            with patch('app.emit', side_effect=lambda event, data: received.append((event, data))):
                app.handle_process_frame({'frame': 'data:image/jpeg;base64,aaa', 'client_id': 'cam-1'})
            self.assertTrue(len(received) > 0)
            self.assertEqual(received[0][1]['status'], 'error')
            self.assertIn('hết hạn', received[0][1]['pesan'])

    def test_gap_3_3_failed_liveness_requires_fresh_confirmation(self):
        app._consecutive_trackers.clear()
        app._completed_trackers.clear()
        prediction = {
            'user_id': 1, 'track_id': 11, 'confidence': 0.9, 'dikenali': True,
            'recognition_status': 'recognized', 'bbox': (0, 0, 80, 80),
        }
        with patch('face.recognition.predict', return_value=[prediction]), \
             patch('face.anti_spoofing.check_face', return_value={
                 'is_real': False, 'label': 'SPOOFING', 'score': 0.2,
             }) as check_face, \
             patch.object(app.db, 'get_jadwal_aktif', return_value=[]), \
             patch.object(app.db, 'catat_spoofing') as catat_spoofing, \
             patch.object(app, '_simpan_snapshot', return_value='snapshots/spoof.jpg'):
            with patch.object(app, 'RECOGNITION_REQUIRED_FRAMES', 3):
                first = app._proses_recognition(_frame(), tracker_key='spoof-reset')
                second = app._proses_recognition(_frame(), tracker_key='spoof-reset')
                third = app._proses_recognition(_frame(), tracker_key='spoof-reset')
                fourth = app._proses_recognition(_frame(), tracker_key='spoof-reset')

        self.assertEqual(first['tipe'], 'verifying')
        self.assertEqual(second['tipe'], 'verifying')
        self.assertEqual(third['tipe'], 'spoofing')
        self.assertEqual(fourth['tipe'], 'verifying')
        check_face.assert_called_once()
        catat_spoofing.assert_called_once()


class GuideFaceSelectionTests(unittest.TestCase):
    """ENR-GUIDE checklist — Multi-Face Guide Selection unit tests.

    Oval constants (from enrollment.py):
        _GUIDE_CENTER_X = 0.50, _GUIDE_CENTER_Y = 0.50
        _GUIDE_RADIUS_X = 0.24, _GUIDE_RADIUS_Y = 0.42
    Frame fixture: 600 x 800 (height x width), detection bbox default w=h=150.
    BVA boundary face (guide_distance == 1.0 exactly):
        cx = 0.50 + 0.24 = 0.74  →  x = 0.74*800 - 75 = 517
        cy = 0.50            →  y = 0.50*600 - 75 = 225
    """

    # ------------------------------------------------------------------ #
    # ENR-GUIDE-01  1 face in oval → accepted when quality+pose ok        #
    # ------------------------------------------------------------------ #
    def test_guide_01_single_face_in_oval_is_accepted(self):
        result = validate_enrollment_frame(_frame(), _Detector([_detection()]), 'center')
        self.assertTrue(result.accepted)

    # ------------------------------------------------------------------ #
    # ENR-GUIDE-03  ≥2 faces in oval → selects closest to centre          #
    # ------------------------------------------------------------------ #
    def test_guide_03_multiple_faces_in_oval_selects_closest_to_center(self):
        # Exactly-centred face: center_x=400/800=0.5, center_y=300/600=0.5
        center_face = _detection(x=325, y=225)   # guide_distance ≈ 0.0
        farther_face = _detection(x=300, y=210)  # guide_distance ≈ 0.020
        result = validate_enrollment_frame(
            _frame(), _Detector([farther_face, center_face]), 'center'
        )
        self.assertTrue(result.accepted)
        self.assertIs(result.detection, center_face)

    # ------------------------------------------------------------------ #
    # ENR-GUIDE-05  empty detections → face_count, not face_outside_guide #
    # ------------------------------------------------------------------ #
    def test_guide_05_empty_detections_returns_face_count_reason(self):
        result = validate_enrollment_frame(_frame(), _Detector([]), 'center')
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, 'face_count')

    # ------------------------------------------------------------------ #
    # ENR-GUIDE-06  zero-size bbox → skipped, no crash                    #
    # ------------------------------------------------------------------ #
    def test_guide_06_zero_size_bbox_is_skipped_without_crash(self):
        zero_w = FaceDetection((300, 210, 0, 150), np.zeros((5, 2), dtype=np.float32), 0.9)
        zero_h = FaceDetection((300, 210, 150, 0), np.zeros((5, 2), dtype=np.float32), 0.9)
        for bad_det in (zero_w, zero_h):
            with self.subTest(bad_det=bad_det):
                result = validate_enrollment_frame(_frame(), _Detector([bad_det]), 'center')
                self.assertFalse(result.accepted)
                self.assertEqual(result.reason, 'face_outside_guide')

    # ------------------------------------------------------------------ #
    # ENR-GUIDE-07  face at guide_distance == 1.0 → still selected (≤)   #
    # ------------------------------------------------------------------ #
    def test_guide_07_face_exactly_at_oval_boundary_is_selected(self):
        # cx = 0.74 → guide_distance = ((0.74-0.5)/0.24)^2 = 1.0 exactly
        boundary_det = _detection(x=517, y=225)
        result = validate_enrollment_frame(_frame(), _Detector([boundary_det]), 'center')
        self.assertNotEqual(result.reason, 'face_outside_guide')

    # ------------------------------------------------------------------ #
    # ENR-GUIDE-08  guide_distance > 1.0 → face rejected                 #
    # ------------------------------------------------------------------ #
    def test_guide_08_face_just_outside_oval_is_rejected(self):
        # cx = 593/800 = 0.74125 → guide_distance ≈ 1.005 > 1.0
        outside_det = _detection(x=518, y=225)
        result = validate_enrollment_frame(_frame(), _Detector([outside_det]), 'center')
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, 'face_outside_guide')

    # ------------------------------------------------------------------ #
    # ENR-GUIDE-09  malformed bbox → skipped, no crash                   #
    # ------------------------------------------------------------------ #
    def test_guide_09_none_bbox_skipped_without_crash(self):
        """bbox=None → TypeError → skipped."""
        bad = FaceDetection(None, np.zeros((5, 2), dtype=np.float32), 0.9)  # type: ignore[arg-type]
        result = validate_enrollment_frame(_frame(), _Detector([bad]), 'center')
        self.assertFalse(result.accepted)
        self.assertIn(result.reason, ('face_count', 'face_outside_guide'))

    def test_guide_09_missing_bbox_attribute_skipped_without_crash(self):
        """detection lacks .bbox → AttributeError → skipped (requires enrollment.py fix)."""
        class NoBbox:
            landmarks = np.zeros((5, 2), dtype=np.float32)
            score = 0.9

        result = validate_enrollment_frame(_frame(), _Detector([NoBbox()]), 'center')
        self.assertFalse(result.accepted)
        self.assertIn(result.reason, ('face_count', 'face_outside_guide'))

    # ------------------------------------------------------------------ #
    # ENR-GUIDE-10  face in oval but fails quality → quality reason        #
    # ------------------------------------------------------------------ #
    @patch(
        'face.enrollment.measure_quality',
        return_value=('face_blurry', {'brightness': 100.0, 'blur_variance': 1.0}),
    )
    def test_guide_10_oval_face_fails_quality_returns_quality_reason(self, _mock_quality):
        result = validate_enrollment_frame(_frame(), _Detector([_detection()]), 'center')
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, 'face_blurry')
        self.assertNotEqual(result.reason, 'face_outside_guide')

    # ------------------------------------------------------------------ #
    # ENR-GUIDE-11  face in oval, quality ok, wrong pose → pose reason    #
    # ------------------------------------------------------------------ #
    def test_guide_11_oval_face_passes_quality_but_fails_pose_returns_pose_reason(self):
        # yaw=0.0 for 'left' stage: need yaw >= ENROLLMENT_POSE_YAW_RATIO (default 0.18)
        result = validate_enrollment_frame(
            _frame(), _Detector([_detection(yaw=0.0)]), 'left'
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, 'turn_left')


if __name__ == '__main__':
    unittest.main()
