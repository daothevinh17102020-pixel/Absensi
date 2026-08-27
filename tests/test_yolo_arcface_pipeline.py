import unittest

import cv2
import numpy as np

from face.yolo_arcface import (
    FaceDetection, SpatialFaceTracker, _as_prediction_rows, evaluate_quality,
    limit_detections, measure_quality, YoloFaceDetector,
)
from face.recognition import _appearance_changed


def _detection(x=20, y=20, width=100, height=100, score=0.9):
    landmarks = np.asarray([
        [x + 30, y + 35], [x + 70, y + 35], [x + 50, y + 55],
        [x + 35, y + 80], [x + 65, y + 80],
    ], dtype=np.float32)
    return FaceDetection((x, y, width, height), landmarks, score)


class YoloContractTests(unittest.TestCase):
    def test_decoded_yolo_rows_accept_n_by_15_and_15_by_n(self):
        rows = np.arange(30, dtype=np.float32).reshape(2, 15)
        self.assertTrue(np.array_equal(_as_prediction_rows(rows), rows))
        self.assertTrue(np.array_equal(_as_prediction_rows(rows.T), rows))

    def test_contract_rejects_model_without_five_landmarks(self):
        with self.assertRaisesRegex(RuntimeError, '5 landmarks'):
            _as_prediction_rows(np.zeros((2, 14), dtype=np.float32))

    def test_post_nms_budget_keeps_top_ten_detector_scores(self):
        detections = [
            _detection(x=index * 120, score=score)
            for index, score in enumerate([
                0.31, 0.99, 0.47, 0.82, 0.76, 0.64,
                0.91, 0.55, 0.88, 0.43, 0.72, 0.95,
            ])
        ]

        limited = limit_detections(detections, 10)

        self.assertEqual(len(limited), 10)
        self.assertEqual(
            [item.score for item in limited],
            sorted([item.score for item in detections], reverse=True)[:10],
        )

    def test_detector_applies_top_ten_budget_after_nms(self):
        detector = object.__new__(YoloFaceDetector)
        detector.input_size = 640
        detector.confidence = 0.1
        detector.nms_iou = 0.45
        detector.max_detections = 10
        detector.input = type('Input', (), {'name': 'images'})()
        detector.output_names = ['output']

        scores = [
            0.31, 0.99, 0.47, 0.82, 0.76, 0.64,
            0.91, 0.55, 0.88, 0.43, 0.72, 0.95,
        ]
        rows = []
        for index, score in enumerate(scores):
            center_x = 25 + index * 50
            rows.append([
                center_x, 100, 40, 40, score,
                center_x - 10, 92, center_x + 10, 92, center_x, 100,
                center_x - 8, 110, center_x + 8, 110,
            ])

        detector.session = type('Session', (), {
            'run': lambda self, output_names, feeds: [
                np.asarray(rows, dtype=np.float32)
            ]
        })()

        detected = detector.detect(np.zeros((640, 640, 3), dtype=np.uint8))

        self.assertEqual(len(detected), 10)
        self.assertTrue(np.allclose(
            [item.score for item in detected],
            sorted(scores, reverse=True)[:10],
        ))


class QualityAndTrackingTests(unittest.TestCase):
    def test_quality_reports_small_face_before_embedding(self):
        image = np.full((120, 120, 3), 130, dtype=np.uint8)
        reason = evaluate_quality(
            image, _detection(width=40, height=40), min_size=80,
            min_brightness=45, max_brightness=220, min_blur=40,
        )
        self.assertEqual(reason, 'face_too_small')

    # --- RT-DET-02 + RT-QLT-01: missing quality branches ---

    def test_quality_reports_face_too_dark(self):
        """RT-QLT-01: mặt tối trả 'face_too_dark'."""
        image = np.full((200, 200, 3), 10, dtype=np.uint8)  # rất tối
        reason = evaluate_quality(
            image, _detection(), min_size=30,
            min_brightness=45, max_brightness=220, min_blur=5,
        )
        self.assertEqual(reason, 'face_too_dark')

    def test_quality_reports_face_too_bright(self):
        """RT-QLT-01: mặt quá sáng trả 'face_too_bright'."""
        image = np.full((200, 200, 3), 250, dtype=np.uint8)  # rất sáng
        reason = evaluate_quality(
            image, _detection(), min_size=30,
            min_brightness=45, max_brightness=220, min_blur=5,
        )
        self.assertEqual(reason, 'face_too_bright')

    def test_quality_reports_face_blurry(self):
        """RT-QLT-01: mặt mờ (laplacian var thấp) trả 'face_blurry'."""
        # Tạo ảnh hoàn toàn đồng nhất → laplacian variance = 0
        image = np.full((200, 200, 3), 130, dtype=np.uint8)
        reason = evaluate_quality(
            image, _detection(), min_size=30,
            min_brightness=45, max_brightness=220, min_blur=40,
        )
        self.assertEqual(reason, 'face_blurry')

    def test_quality_reports_landmarks_invalid_nan(self):
        """RT-DET-02: landmark chứa NaN trả 'landmarks_invalid'."""
        image = np.full((200, 200, 3), 130, dtype=np.uint8)
        bad_landmarks = np.full((5, 2), np.nan, dtype=np.float32)
        detection = FaceDetection((20, 20, 100, 100), bad_landmarks, 0.9)
        reason = evaluate_quality(
            image, detection, min_size=30,
            min_brightness=45, max_brightness=220, min_blur=5,
        )
        self.assertEqual(reason, 'landmarks_invalid')

    def test_quality_reports_face_out_of_box(self):
        """RT-DET-02: landmark nằm ngoài bbox trả 'face_out_of_box'."""
        image = np.full((300, 300, 3), 130, dtype=np.uint8)
        # Landmark xa bên ngoài bbox
        outside_landmarks = np.asarray([
            [200, 200], [210, 200], [205, 210],
            [200, 220], [210, 220],
        ], dtype=np.float32)
        detection = FaceDetection((20, 20, 50, 50), outside_landmarks, 0.9)
        reason = evaluate_quality(
            image, detection, min_size=30,
            min_brightness=45, max_brightness=220, min_blur=5,
        )
        self.assertEqual(reason, 'face_out_of_box')

    def test_quality_passes_good_face(self):
        """Khuôn mặt đạt chất lượng trả None (không lỗi)."""
        # Tạo ảnh noise ngẫu nhiên trong khoảng brightness hợp lệ
        rng = np.random.RandomState(42)
        image = rng.randint(80, 180, (200, 200, 3), dtype=np.uint8)
        reason = evaluate_quality(
            image, _detection(), min_size=30,
            min_brightness=45, max_brightness=220, min_blur=5,
        )
        self.assertIsNone(reason)

    def test_blur_score_is_stable_when_same_face_box_is_larger(self):
        rng = np.random.RandomState(7)
        canonical = rng.randint(70, 190, (224, 224, 3), dtype=np.uint8)
        enlarged = cv2.resize(canonical, (448, 448), interpolation=cv2.INTER_NEAREST)
        _, canonical_metrics = measure_quality(
            canonical, _detection(x=0, y=0, width=224, height=224), min_size=30,
            min_brightness=45, max_brightness=220, min_blur=0,
        )
        _, enlarged_metrics = measure_quality(
            enlarged, _detection(x=0, y=0, width=448, height=448), min_size=30,
            min_brightness=45, max_brightness=220, min_blur=0,
        )
        self.assertAlmostEqual(
            canonical_metrics['blur_variance'], enlarged_metrics['blur_variance'], delta=1.0
        )

    def test_tracker_keeps_id_for_same_face_and_creates_new_one(self):
        tracker = SpatialFaceTracker(iou_threshold=0.25, ttl_seconds=2)
        first = tracker.update([_detection()])[0][0].track_id
        same = tracker.update([_detection(x=24, y=22)])[0][0].track_id
        other = tracker.update([_detection(x=200, y=20)])[0][0].track_id
        self.assertEqual(first, same)
        self.assertNotEqual(first, other)


class AppearanceChangeTests(unittest.TestCase):
    """RT-TRK-02: appearance_changed phải phát hiện khi người mới thế chỗ."""

    def test_appearance_changed_detects_different_face(self):
        """Hai luminance fingerprint khác nhau đủ ngưỡng → True."""
        face_a = np.full((16, 16), 50.0, dtype=np.float32)
        face_b = np.full((16, 16), 200.0, dtype=np.float32)
        self.assertTrue(_appearance_changed(face_a, face_b))

    def test_appearance_unchanged_for_same_face(self):
        """Cùng fingerprint → False."""
        face = np.full((16, 16), 120.0, dtype=np.float32)
        self.assertFalse(_appearance_changed(face, face))

    def test_appearance_changed_when_previous_is_none(self):
        """Lần đầu detect (previous=None) → True (cần embed)."""
        face = np.full((16, 16), 120.0, dtype=np.float32)
        self.assertTrue(_appearance_changed(face, None))
        self.assertTrue(_appearance_changed(None, face))


if __name__ == '__main__':
    unittest.main()
